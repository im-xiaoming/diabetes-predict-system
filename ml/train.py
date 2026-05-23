from pathlib import Path
import json
import logging
import sys
import tempfile
import time

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score, hamming_loss, recall_score
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline

try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

import argparse

from ml.preprocessing import build_preprocessor, clean_data, load_data, split_xy
from ml.tracking import log_metrics, log_model, log_params, log_report, start_run
from ml.tune import tune_all
from ml.registry import get_champion_metrics, register_best_model, restore_champion_model


DATA_PATH = ROOT_DIR / "data" / "data.csv"
MODEL_PATH = ROOT_DIR / "ml" / "artifacts" / "model.pkl"
TRAINING_CONFIG_PATH = ROOT_DIR / "configs" / "model_training_config.json"
TEST_SIZE = 0.2
RANDOM_STATE = 42
LOGGER = logging.getLogger("ml.train")


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )


def atomic_joblib_dump(obj, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
        joblib.dump(obj, tmp_path)
        tmp_path.replace(destination)
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


def load_training_config(path=TRAINING_CONFIG_PATH):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        LOGGER.warning("training_config_invalid path=%s", path)
        return {}


def config_value(config, key, fallback):
    value = (config or {}).get(key)
    return fallback if value is None else value


def make_models(config=None):
    enabled = set((config or {}).get("enabled_models") or ["logistic_regression", "random_forest", "xgboost"])
    search_space = (config or {}).get("search_space", {})
    random_state = int((config or {}).get("optuna", {}).get("random_state", RANDOM_STATE))
    models = {
        "logistic_regression": Pipeline(
            [
                ("pp", build_preprocessor()),
                (
                    "mdl",
                    MultiOutputClassifier(
                        LogisticRegression(
                            max_iter=int(search_space.get("logistic_regression", {}).get("max_iter", 2000)),
                            class_weight=search_space.get("logistic_regression", {}).get("class_weight", "balanced"),
                        )
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("pp", build_preprocessor()),
                (
                    "mdl",
                    MultiOutputClassifier(
                        RandomForestClassifier(
                            n_estimators=300,
                            random_state=random_state,
                            class_weight=search_space.get("random_forest", {}).get("class_weight", "balanced"),
                            n_jobs=int(search_space.get("random_forest", {}).get("n_jobs", -1)),
                        )
                    ),
                ),
            ]
        ),
    }
    if XGBClassifier:
        models["xgboost"] = Pipeline(
            [
                ("pp", build_preprocessor()),
                (
                    "mdl",
                    MultiOutputClassifier(
                        XGBClassifier(
                            n_estimators=200,
                            max_depth=4,
                            learning_rate=0.05,
                            subsample=0.9,
                            colsample_bytree=0.9,
                            eval_metric="logloss",
                            random_state=random_state,
                        )
                    ),
                ),
            ]
        )
    return {name: model for name, model in models.items() if name in enabled}


def label_acc(y_true, y_pred):
    return (y_true.to_numpy() == y_pred).mean()


def score_model(name, mdl, x_train, x_test, y_train, y_test, tg):
    started_at = time.monotonic()
    LOGGER.info(
        "model_fit_start model=%s train_rows=%s test_rows=%s",
        name,
        len(x_train),
        len(x_test),
    )
    mdl.fit(x_train, y_train)
    pred = mdl.predict(x_test)
    rep_txt = classification_report(y_test, pred, target_names=tg, zero_division=0)
    rep_js = classification_report(y_test, pred, target_names=tg, zero_division=0, output_dict=True)
    res = {
        "model": name,
        "exact_acc": accuracy_score(y_test, pred),
        "label_acc": label_acc(y_test, pred),
        "f1_micro": f1_score(y_test, pred, average="micro", zero_division=0),
        "f1_macro": f1_score(y_test, pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_test, pred, average="macro", zero_division=0),
        "hamming_loss": hamming_loss(y_test, pred),
    }
    met = {k: v for k, v in res.items() if k != "model"}
    LOGGER.info("model_metrics model=%s metrics=%s", name, pd.Series(met).round(4).to_dict())
    LOGGER.info("classification_report model=%s\n%s", name, rep_txt)
    for t in tg:
        support = int(y_test[t].sum())
        if support < 10:
            LOGGER.warning(
                "low_positive_support target=%s support=%s message=read_metric_with_care",
                t,
                support,
            )
    LOGGER.info("model_fit_done model=%s duration_sec=%.2f", name, time.monotonic() - started_at)
    return res, rep_txt, rep_js


def build_tuned_models(x_train, y_train, n_trials, timeout, log_trials=True, training_config=None):
    started_at = time.monotonic()
    LOGGER.info(
        "optuna_tuning_start n_trials=%s timeout=%s log_trials=%s",
        n_trials,
        timeout,
        log_trials,
    )
    results = tune_all(
        x_train,
        y_train,
        n_trials=n_trials,
        timeout=timeout,
        log_trials=log_trials,
        config=training_config,
    )
    models = {}
    tuned_meta = {}
    for name, r in results.items():
        LOGGER.info(
            "optuna_tuning_result model=%s best_cv_f1_macro=%.4f params=%s",
            name,
            r["best_cv_f1_macro"],
            r["best_params"],
        )
        models[name] = r["pipeline"]
        tuned_meta[name] = {
            "best_params": r["best_params"],
            "best_cv_f1_macro": r["best_cv_f1_macro"],
        }
    LOGGER.info("optuna_tuning_done duration_sec=%.2f", time.monotonic() - started_at)
    return models, tuned_meta


def promotion_decision(candidate_metrics, champion_info, metric, min_delta, force=False):
    candidate_score = candidate_metrics.get(metric)
    if candidate_score is None:
        raise ValueError(f"Candidate metric not found: {metric}")
    if force:
        return True, f"force_promote=true; candidate {metric}={candidate_score:.6f}"
    if not champion_info:
        return True, "no champion found"

    champion_score = champion_info.get("metrics", {}).get(metric)
    if champion_score is None:
        return True, f"champion metric not found: {metric}"

    threshold = champion_score + min_delta
    if candidate_score > threshold:
        return (
            True,
            f"candidate {metric}={candidate_score:.6f} > champion {metric}={champion_score:.6f} + delta {min_delta:.6f}",
        )
    return (
        False,
        f"candidate {metric}={candidate_score:.6f} <= champion {metric}={champion_score:.6f} + delta {min_delta:.6f}",
    )


def main(
    data_path=DATA_PATH,
    tune=False,
    n_trials=30,
    timeout=None,
    register=False,
    promotion_metric="f1_macro",
    promotion_min_delta=0.0,
    force_promote=False,
    log_optuna_trials=True,
    training_config=None,
):
    started_at = time.monotonic()
    data_path = Path(data_path)
    LOGGER.info(
        "train_start data=%s tune=%s n_trials=%s timeout=%s register=%s promotion_metric=%s min_delta=%s force_promote=%s",
        data_path,
        tune,
        n_trials,
        timeout,
        register,
        promotion_metric,
        promotion_min_delta,
        force_promote,
    )
    LOGGER.info("model_output_path=%s", MODEL_PATH)
    if training_config:
        LOGGER.info("training_config=%s", training_config)
    df = load_data(data_path)
    raw_n = len(df)
    df = clean_data(df)
    LOGGER.info("rows_raw=%s", raw_n)
    LOGGER.info("rows_clean=%s", len(df))
    LOGGER.info("duplicates_dropped=%s", raw_n - len(df))
    x, y, ft, tg, num, cat = split_xy(df)
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )
    LOGGER.info(
        "train_test_split train_rows=%s test_rows=%s features=%s targets=%s",
        len(x_train),
        len(x_test),
        ft,
        tg,
    )
    base = {
        "targets": tg,
        "features": ft,
        "rows_raw": raw_n,
        "rows_clean": len(df),
        "duplicates_dropped": raw_n - len(df),
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "data_path": str(data_path),
        "promotion_metric": promotion_metric,
        "promotion_min_delta": promotion_min_delta,
    }
    if tune:
        models_iter, tuned_meta = build_tuned_models(
            x_train,
            y_train,
            n_trials,
            timeout,
            log_trials=log_optuna_trials,
            training_config=training_config,
        )
    else:
        models_iter, tuned_meta = make_models(training_config), {}
    rows = []
    best_name = None
    best_mdl = None
    best_f1 = -1
    best_metrics = None
    for name, mdl in models_iter.items():
        try:
            LOGGER.info("mlflow_run_start model=%s", name)
            with start_run(name):
                res, rep_txt, rep_js = score_model(name, mdl, x_train, x_test, y_train, y_test, tg)
                met = {k: v for k, v in res.items() if k != "model"}
                params = dict(base)
                params["model_name"] = name
                if name in tuned_meta:
                    params["tuned"] = True
                    params["best_params"] = tuned_meta[name]["best_params"]
                    params["best_cv_f1_macro"] = tuned_meta[name]["best_cv_f1_macro"]
                log_params(params)
                log_metrics(met)
                log_report(rep_txt, rep_js)
                log_model(mdl)
            LOGGER.info("mlflow_run_done model=%s", name)
            rows.append(res)
            if res["f1_macro"] > best_f1:
                best_f1 = res["f1_macro"]
                best_name = name
                best_mdl = mdl
                best_metrics = met
        except Exception as exc:
            LOGGER.exception("model_skipped model=%s error=%s", name, exc)
    if not rows:
        raise RuntimeError("No model trained successfully")
    cmp = pd.DataFrame(rows).sort_values("f1_macro", ascending=False)
    LOGGER.info("model_comparison\n%s", cmp.round(4).to_string(index=False))
    LOGGER.info("best_candidate model=%s f1_macro=%.4f metrics=%s", best_name, best_f1, best_metrics)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": best_mdl,
        "model_name": best_name,
        "features": ft,
        "targets": tg,
        "numeric": num,
        "categorical": cat,
    }
    champion_info = get_champion_metrics() if register else None
    if champion_info:
        LOGGER.info("champion_found version=%s metrics=%s", champion_info["version"], champion_info["metrics"])
    elif register:
        LOGGER.info("champion_missing")
    promoted, reason = promotion_decision(
        best_metrics,
        champion_info,
        promotion_metric,
        promotion_min_delta,
        force=force_promote,
    )
    LOGGER.info("promotion_decision=%s", "promote" if promoted else "reject")
    LOGGER.info("promotion_reason=%s", reason)

    if not promoted:
        try:
            restore_champion_model(MODEL_PATH)
            joblib.load(MODEL_PATH)
        except Exception as exc:
            promoted = True
            reason = f"candidate promoted because champion artifact could not be restored in this environment: {exc}"
            LOGGER.warning("champion_restore_failed error=%s", exc)
        else:
            champion_version = champion_info["version"] if champion_info else "unknown"
            LOGGER.info("restored_model=%s", MODEL_PATH)
            LOGGER.info("kept_champion_version=%s", champion_version)
            LOGGER.info("train_done promoted=false duration_sec=%.2f", time.monotonic() - started_at)
            return {
                "promoted": False,
                "candidate_model": best_name,
                "candidate_metrics": best_metrics,
                "champion": champion_info,
                "reason": reason,
            }

    atomic_joblib_dump(bundle, MODEL_PATH)
    LOGGER.info("saved_model=%s bytes=%s", MODEL_PATH, MODEL_PATH.stat().st_size)

    if register:
        reg_params = dict(base)
        reg_params["model_name"] = best_name
        reg_params["promoted"] = True
        reg_params["promotion_reason"] = reason
        if best_name in tuned_meta:
            reg_params["best_params"] = tuned_meta[best_name]["best_params"]
            reg_params["best_cv_f1_macro"] = tuned_meta[best_name]["best_cv_f1_macro"]
        info = register_best_model(bundle, best_name, best_metrics, reg_params)
        LOGGER.info("registered_model=%s", info)

    LOGGER.info("train_done promoted=true duration_sec=%.2f", time.monotonic() - started_at)
    return {
        "promoted": True,
        "candidate_model": best_name,
        "candidate_metrics": best_metrics,
        "reason": reason,
    }


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=str(DATA_PATH), help="CSV training data path")
    p.add_argument("--config", default=str(TRAINING_CONFIG_PATH), help="JSON training config path")
    p.add_argument("--tune", action="store_true", help="Use Optuna for hyperparameter tuning")
    p.add_argument("--n-trials", type=int, default=30, help="Number of trials per model")
    p.add_argument("--timeout", type=int, default=None, help="Timeout in seconds per model")
    p.add_argument("--register", action="store_true", help="Register best model in MLflow registry")
    p.add_argument("--promotion-metric", default="f1_macro", help="Metric used to compare candidate with champion")
    p.add_argument("--promotion-min-delta", type=float, default=0.0, help="Minimum metric improvement required")
    p.add_argument("--force-promote", action="store_true", help="Promote candidate even if it is worse than champion")
    p.add_argument(
        "--no-log-optuna-trials",
        action="store_true",
        help="Do not create one MLflow run for each Optuna trial",
    )
    return p.parse_args()


if __name__ == "__main__":
    configure_logging()
    args = parse_args()
    training_config = load_training_config(args.config)
    timeout = config_value(training_config, "timeout", args.timeout)
    if timeout == 0:
        timeout = None
    main(
        data_path=args.data,
        tune=bool(config_value(training_config, "tune", args.tune)),
        n_trials=int(config_value(training_config, "n_trials", args.n_trials)),
        timeout=timeout,
        register=bool(config_value(training_config, "register", args.register)),
        promotion_metric=str(config_value(training_config, "promotion_metric", args.promotion_metric)),
        promotion_min_delta=float(config_value(training_config, "promotion_min_delta", args.promotion_min_delta)),
        force_promote=bool(config_value(training_config, "force_promote", args.force_promote)),
        log_optuna_trials=bool(config_value(training_config, "log_optuna_trials", not args.no_log_optuna_trials)),
        training_config=training_config,
    )
