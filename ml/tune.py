from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import optuna
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


N_SPLITS = 3
RANDOM_STATE = 42


def _cv_f1_macro(pipe, x, y):
    kf = KFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    scores = []
    for tr, te in kf.split(x):
        x_tr, x_te = x.iloc[tr], x.iloc[te]
        y_tr, y_te = y.iloc[tr], y.iloc[te]
        pipe.fit(x_tr, y_tr)
        pred = pipe.predict(x_te)
        scores.append(f1_score(y_te, pred, average="macro", zero_division=0))
    return sum(scores) / len(scores)


def _build_pipe(estimator):
    return Pipeline(
        [
            ("pp", build_preprocessor()),
            ("mdl", MultiOutputClassifier(estimator)),
        ]
    )


def _objective_logreg(trial, x, y):
    params = {
        "C": trial.suggest_float("C", 1e-3, 10.0, log=True),
        "penalty": trial.suggest_categorical("penalty", ["l2"]),
        "solver": trial.suggest_categorical("solver", ["lbfgs", "liblinear"]),
        "max_iter": 2000,
        "class_weight": "balanced",
    }
    est = LogisticRegression(**params)
    return _cv_f1_macro(_build_pipe(est), x, y)


def _objective_rf(trial, x, y):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 600, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 20),
        "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", None]),
        "class_weight": "balanced",
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    }
    est = RandomForestClassifier(**params)
    return _cv_f1_macro(_build_pipe(est), x, y)


def _objective_xgb(trial, x, y):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 600, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma": trial.suggest_float("gamma", 0.0, 5.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        "eval_metric": "logloss",
        "random_state": RANDOM_STATE,
    }
    est = XGBClassifier(**params)
    return _cv_f1_macro(_build_pipe(est), x, y)


OBJECTIVES = {
    "logistic_regression": _objective_logreg,
    "random_forest": _objective_rf,
}
if XGBClassifier:
    OBJECTIVES["xgboost"] = _objective_xgb


def _final_estimator(name, params):
    if name == "logistic_regression":
        return LogisticRegression(max_iter=2000, class_weight="balanced", **params)
    if name == "random_forest":
        return RandomForestClassifier(
            class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1, **params
        )
    if name == "xgboost":
        return XGBClassifier(eval_metric="logloss", random_state=RANDOM_STATE, **params)
    raise ValueError(f"unknown model: {name}")


def tune_model(name, x, y, n_trials=30, timeout=None):
    if name not in OBJECTIVES:
        raise ValueError(f"no objective for {name}")
    objective = OBJECTIVES[name]
    sampler = optuna.samplers.TPESampler(seed=RANDOM_STATE)
    study = optuna.create_study(direction="maximize", sampler=sampler, study_name=f"tune_{name}")
    study.optimize(lambda t: objective(t, x, y), n_trials=n_trials, timeout=timeout, show_progress_bar=False)
    best_params = study.best_params
    best_score = study.best_value
    pipe = _build_pipe(_final_estimator(name, best_params))
    return {
        "name": name,
        "best_params": best_params,
        "best_cv_f1_macro": best_score,
        "pipeline": pipe,
        "study": study,
    }


def tune_all(x, y, n_trials=30, timeout=None):
    return {name: tune_model(name, x, y, n_trials=n_trials, timeout=timeout) for name in OBJECTIVES}
