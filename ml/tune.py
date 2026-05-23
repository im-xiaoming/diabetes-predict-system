from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import optuna
import mlflow
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import KFold
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline

try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

from ml.preprocessing import build_preprocessor
from ml.tracking import setup_tracking


N_SPLITS = 3
RANDOM_STATE = 42


def _cv_f1_macro(pipe, x, y, config=None):
    n_splits = int(_optuna_value(config, "n_splits", N_SPLITS))
    random_state = int(_optuna_value(config, "random_state", RANDOM_STATE))
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    scores = []
    for tr, te in kf.split(x):
        x_tr, x_te = x.iloc[tr], x.iloc[te]
        y_tr, y_te = y.iloc[tr], y.iloc[te]
        pipe.fit(x_tr, y_tr)
        pred = pipe.predict(x_te)
        scores.append(f1_score(y_te, pred, average="macro", zero_division=0))
    return sum(scores) / len(scores)


def _model_space(config, name):
    return (config or {}).get("search_space", {}).get(name, {})


def _optuna_value(config, name, default):
    return (config or {}).get("optuna", {}).get(name, default)


def _int_space(space, key, default_low, default_high, default_step=None):
    raw = space.get(key, {})
    if not isinstance(raw, dict):
        return default_low, default_high, default_step
    return int(raw.get("low", default_low)), int(raw.get("high", default_high)), raw.get("step", default_step)


def _float_space(space, key, default_low, default_high, default_log=False):
    raw = space.get(key, {})
    if not isinstance(raw, dict):
        return default_low, default_high, default_log
    return float(raw.get("low", default_low)), float(raw.get("high", default_high)), bool(raw.get("log", default_log))


def _choices(space, key, default):
    raw = space.get(key, default)
    return raw if isinstance(raw, list) and raw else default


def _build_pipe(estimator):
    return Pipeline(
        [
            ("pp", build_preprocessor()),
            ("mdl", MultiOutputClassifier(estimator)),
        ]
    )


def _objective_logreg(trial, x, y, config=None):
    space = _model_space(config, "logistic_regression")
    c_low, c_high, c_log = _float_space(space, "C", 1e-3, 10.0, True)
    params = {
        "C": trial.suggest_float("C", c_low, c_high, log=c_log),
        "penalty": trial.suggest_categorical("penalty", _choices(space, "penalty", ["l2"])),
        "solver": trial.suggest_categorical("solver", _choices(space, "solver", ["lbfgs", "liblinear"])),
        "max_iter": int(space.get("max_iter", 2000)),
        "class_weight": space.get("class_weight", "balanced"),
    }
    est = LogisticRegression(**params)
    return _cv_f1_macro(_build_pipe(est), x, y, config)


def _objective_rf(trial, x, y, config=None):
    space = _model_space(config, "random_forest")
    n_low, n_high, n_step = _int_space(space, "n_estimators", 100, 600, 50)
    depth_low, depth_high, _ = _int_space(space, "max_depth", 3, 20)
    split_low, split_high, _ = _int_space(space, "min_samples_split", 2, 20)
    leaf_low, leaf_high, _ = _int_space(space, "min_samples_leaf", 1, 10)
    params = {
        "n_estimators": trial.suggest_int("n_estimators", n_low, n_high, step=n_step or 1),
        "max_depth": trial.suggest_int("max_depth", depth_low, depth_high),
        "min_samples_split": trial.suggest_int("min_samples_split", split_low, split_high),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", leaf_low, leaf_high),
        "max_features": trial.suggest_categorical("max_features", _choices(space, "max_features", ["sqrt", "log2", None])),
        "class_weight": space.get("class_weight", "balanced"),
        "random_state": int(_optuna_value(config, "random_state", RANDOM_STATE)),
        "n_jobs": int(space.get("n_jobs", -1)),
    }
    est = RandomForestClassifier(**params)
    return _cv_f1_macro(_build_pipe(est), x, y, config)


def _objective_xgb(trial, x, y, config=None):
    space = _model_space(config, "xgboost")
    n_low, n_high, n_step = _int_space(space, "n_estimators", 100, 600, 50)
    depth_low, depth_high, _ = _int_space(space, "max_depth", 3, 10)
    lr_low, lr_high, lr_log = _float_space(space, "learning_rate", 1e-3, 0.3, True)
    subsample_low, subsample_high, _ = _float_space(space, "subsample", 0.6, 1.0)
    colsample_low, colsample_high, _ = _float_space(space, "colsample_bytree", 0.6, 1.0)
    child_low, child_high, _ = _int_space(space, "min_child_weight", 1, 10)
    gamma_low, gamma_high, _ = _float_space(space, "gamma", 0.0, 5.0)
    reg_low, reg_high, reg_log = _float_space(space, "reg_lambda", 1e-3, 10.0, True)
    params = {
        "n_estimators": trial.suggest_int("n_estimators", n_low, n_high, step=n_step or 1),
        "max_depth": trial.suggest_int("max_depth", depth_low, depth_high),
        "learning_rate": trial.suggest_float("learning_rate", lr_low, lr_high, log=lr_log),
        "subsample": trial.suggest_float("subsample", subsample_low, subsample_high),
        "colsample_bytree": trial.suggest_float("colsample_bytree", colsample_low, colsample_high),
        "min_child_weight": trial.suggest_int("min_child_weight", child_low, child_high),
        "gamma": trial.suggest_float("gamma", gamma_low, gamma_high),
        "reg_lambda": trial.suggest_float("reg_lambda", reg_low, reg_high, log=reg_log),
        "eval_metric": space.get("eval_metric", "logloss"),
        "random_state": int(_optuna_value(config, "random_state", RANDOM_STATE)),
    }
    est = XGBClassifier(**params)
    return _cv_f1_macro(_build_pipe(est), x, y, config)


def _mlflow_param_value(value):
    if value is None:
        return "None"
    return value


def _log_optuna_trial(model_name, study_name, trial, score):
    setup_tracking()
    with mlflow.start_run(
        run_name=f"trial_{trial.number}",
        nested=mlflow.active_run() is not None,
    ):
        mlflow.set_tags(
            {
                "run_type": "optuna_trial",
                "model_family": model_name,
                "study_name": study_name,
            }
        )
        mlflow.log_params(
            {
                "model_name": model_name,
                "trial_number": trial.number,
                "n_splits": N_SPLITS,
                **{k: _mlflow_param_value(v) for k, v in trial.params.items()},
            }
        )
        mlflow.log_metric("cv_f1_macro", float(score))
        mlflow.log_metric("objective_value", float(score))


OBJECTIVES = {
    "logistic_regression": _objective_logreg,
    "random_forest": _objective_rf,
}
if XGBClassifier:
    OBJECTIVES["xgboost"] = _objective_xgb


def _final_estimator(name, params, config=None):
    if name == "logistic_regression":
        space = _model_space(config, "logistic_regression")
        final_params = {
            "max_iter": int(space.get("max_iter", 2000)),
            "class_weight": space.get("class_weight", "balanced"),
            **params,
        }
        return LogisticRegression(**final_params)
    if name == "random_forest":
        space = _model_space(config, "random_forest")
        return RandomForestClassifier(
            class_weight=space.get("class_weight", "balanced"),
            random_state=int(_optuna_value(config, "random_state", RANDOM_STATE)),
            n_jobs=int(space.get("n_jobs", -1)),
            **params,
        )
    if name == "xgboost":
        space = _model_space(config, "xgboost")
        return XGBClassifier(
            eval_metric=space.get("eval_metric", "logloss"),
            random_state=int(_optuna_value(config, "random_state", RANDOM_STATE)),
            **params,
        )
    raise ValueError(f"unknown model: {name}")


def tune_model(name, x, y, n_trials=30, timeout=None, log_trials=True, config=None):
    if name not in OBJECTIVES:
        raise ValueError(f"no objective for {name}")
    objective = OBJECTIVES[name]
    random_state = int(_optuna_value(config, "random_state", RANDOM_STATE))
    n_splits = int(_optuna_value(config, "n_splits", N_SPLITS))
    sampler = optuna.samplers.TPESampler(seed=random_state)
    study_name = f"tune_{name}"
    study = optuna.create_study(direction="maximize", sampler=sampler, study_name=study_name)

    def wrapped_objective(trial):
        score = objective(trial, x, y, config)
        if log_trials:
            _log_optuna_trial(name, study_name, trial, score)
        return score

    if log_trials:
        setup_tracking()
        with mlflow.start_run(
            run_name=f"optuna_{name}",
            nested=mlflow.active_run() is not None,
        ):
            mlflow.set_tags(
                {
                    "run_type": "optuna_study",
                    "model_family": name,
                    "study_name": study_name,
                }
            )
            mlflow.log_params(
                {
                    "model_name": name,
                    "n_trials": n_trials,
                    "timeout": _mlflow_param_value(timeout),
                    "n_splits": n_splits,
                    "random_state": random_state,
                }
            )
            study.optimize(wrapped_objective, n_trials=n_trials, timeout=timeout, show_progress_bar=False)
            mlflow.log_metric("best_cv_f1_macro", float(study.best_value))
            mlflow.log_params(
                {f"best_{k}": _mlflow_param_value(v) for k, v in study.best_params.items()}
            )
    else:
        study.optimize(wrapped_objective, n_trials=n_trials, timeout=timeout, show_progress_bar=False)
    best_params = study.best_params
    best_score = study.best_value
    pipe = _build_pipe(_final_estimator(name, best_params, config))
    return {
        "name": name,
        "best_params": best_params,
        "best_cv_f1_macro": best_score,
        "pipeline": pipe,
        "study": study,
    }


def tune_all(x, y, n_trials=30, timeout=None, log_trials=True, config=None):
    enabled = (config or {}).get("enabled_models") or list(OBJECTIVES)
    return {
        name: tune_model(name, x, y, n_trials=n_trials, timeout=timeout, log_trials=log_trials, config=config)
        for name in enabled
        if name in OBJECTIVES
    }
