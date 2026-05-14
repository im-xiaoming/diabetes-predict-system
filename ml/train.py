from pathlib import Path
import sys

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

from ml.preprocessing import build_preprocessor, clean_data, load_data, split_xy
from ml.tracking import log_metrics, log_model, log_params, log_report, start_run


DATA_PATH = ROOT_DIR / "data" / "data.csv"
MODEL_PATH = ROOT_DIR / "ml" / "artifacts" / "model.pkl"
TEST_SIZE = 0.2
RANDOM_STATE = 42


def make_models():
    models = {
        "logistic_regression": Pipeline(
            [
                ("pp", build_preprocessor()),
                (
                    "mdl",
                    MultiOutputClassifier(
                        LogisticRegression(max_iter=2000, class_weight="balanced")
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
                            random_state=42,
                            class_weight="balanced",
                            n_jobs=-1,
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
                            random_state=42,
                        )
                    ),
                ),
            ]
        )
    return models


def label_acc(y_true, y_pred):
    return (y_true.to_numpy() == y_pred).mean()


def score_model(name, mdl, x_train, x_test, y_train, y_test, tg):
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
    print(f"\n{name}")
    print(pd.Series(met).round(4).to_string())
    print("\nclassification_report")
    print(rep_txt)
    for t in tg:
        support = int(y_test[t].sum())
        if support < 10:
            print(f"{t}: positive support thap ({support}), can doc metric can than")
    return res, rep_txt, rep_js


def main():
    df = load_data(DATA_PATH)
    raw_n = len(df)
    df = clean_data(df)
    print(f"rows_raw: {raw_n}")
    print(f"rows_clean: {len(df)}")
    print(f"duplicates_dropped: {raw_n - len(df)}")
    x, y, ft, tg, num, cat = split_xy(df)
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )
    base = {
        "targets": tg,
        "features": ft,
        "rows_raw": raw_n,
        "rows_clean": len(df),
        "duplicates_dropped": raw_n - len(df),
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
    }
    rows = []
    best_name = None
    best_mdl = None
    best_f1 = -1
    for name, mdl in make_models().items():
        try:
            with start_run(name):
                res, rep_txt, rep_js = score_model(name, mdl, x_train, x_test, y_train, y_test, tg)
                met = {k: v for k, v in res.items() if k != "model"}
                params = dict(base)
                params["model_name"] = name
                log_params(params)
                log_metrics(met)
                log_report(rep_txt, rep_js)
                log_model(mdl)
            rows.append(res)
            if res["f1_macro"] > best_f1:
                best_f1 = res["f1_macro"]
                best_name = name
                best_mdl = mdl
        except Exception as exc:
            print(f"\n{name} skipped: {exc}")
    if not rows:
        raise RuntimeError("No model trained successfully")
    cmp = pd.DataFrame(rows).sort_values("f1_macro", ascending=False)
    print("\nmodel_comparison")
    print(cmp.round(4).to_string(index=False))
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": best_mdl,
        "model_name": best_name,
        "features": ft,
        "targets": tg,
        "numeric": num,
        "categorical": cat,
    }
    joblib.dump(bundle, MODEL_PATH)
    print(f"\nsaved_model: {MODEL_PATH}")


if __name__ == "__main__":
    main()
