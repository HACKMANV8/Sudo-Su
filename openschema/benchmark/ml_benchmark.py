from __future__ import annotations

import time
from typing import Any, Dict

import numpy as np
import pandas as pd


def _is_classification(y: pd.Series) -> bool:
    if y.dtype == bool:
        return True
    if y.dtype.kind in {"i", "u"} and y.nunique() <= 20:
        return True
    if y.dtype.kind in {"O", "b"}:
        return True
    return False


def _preprocess(df: pd.DataFrame, target: str) -> tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    y = df[target]
    X = df.drop(columns=[target])
    num_cols = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
    cat_cols = [c for c in X.columns if c not in num_cols]
    # Simple numeric impute
    Xn = X[num_cols].apply(pd.to_numeric, errors="coerce").fillna(X[num_cols].mean()).to_numpy(dtype=float) if num_cols else np.zeros((len(X), 0))
    # One-hot for small-cardinality cats
    Xc_list = []
    for c in cat_cols:
        vc = X[c].astype(str)
        cats = list(vc.value_counts().index[:20])
        oh = np.zeros((len(vc), len(cats)), dtype=float)
        idx = {v: i for i, v in enumerate(cats)}
        for i, v in enumerate(vc):
            j = idx.get(v)
            if j is not None:
                oh[i, j] = 1.0
        Xc_list.append(oh)
    Xc = np.concatenate(Xc_list, axis=1) if Xc_list else np.zeros((len(X), 0))
    features = np.concatenate([Xn, Xc], axis=1)
    return features, y.to_numpy(), {"num_cols": num_cols, "cat_cols": cat_cols}


def _train_model(X: np.ndarray, y: np.ndarray, classification: bool, seed: int = 0):
    # Try xgboost
    model = None
    try:
        import xgboost as xgb  # type: ignore

        if classification:
            model = xgb.XGBClassifier(n_estimators=50, max_depth=4, subsample=0.8, colsample_bytree=0.8, random_state=seed, n_jobs=1, verbosity=0)
        else:
            model = xgb.XGBRegressor(n_estimators=50, max_depth=4, subsample=0.8, colsample_bytree=0.8, random_state=seed, n_jobs=1, verbosity=0)
        model.fit(X, y)
        return model
    except Exception:
        pass
    # Fallback to RandomForest
    try:
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor  # type: ignore

        if classification:
            model = RandomForestClassifier(n_estimators=50, random_state=seed)
        else:
            model = RandomForestRegressor(n_estimators=50, random_state=seed)
        model.fit(X, y)
        return model
    except Exception:
        # Minimal fallback dummy
        class _Dummy:
            def predict(self, X):
                if classification:
                    return np.zeros((len(X),), dtype=int)
                return np.zeros((len(X),), dtype=float)
        return _Dummy()


def evaluate_ml_utility(
    synthetic_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    target_column: str,
    model: str = "xgb",
    test_fraction: float = 0.2,
    seed: int = 0,
) -> Dict[str, Any]:
    t0 = time.time()
    # Drop rows with missing target
    s = synthetic_df.dropna(subset=[target_column]).reset_index(drop=True)
    r = reference_df.dropna(subset=[target_column]).reset_index(drop=True)
    # Split reference into train/test to evaluate on real distribution
    n = len(r)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    test_n = max(1, int(test_fraction * n))
    test_idx = idx[:test_n]
    train_idx = idx[test_n:]
    r_train = r.iloc[train_idx]
    r_test = r.iloc[test_idx]

    # Preprocess
    X_s, y_s, info = _preprocess(s, target_column)
    X_rt, y_rt, _ = _preprocess(r_train, target_column)
    X_re, y_re, _ = _preprocess(r_test, target_column)
    is_cls = _is_classification(pd.Series(y_s))

    # Train on synthetic, test on real
    model_obj = _train_model(X_s, y_s, is_cls, seed=seed)
    # Synthetic train score via simple holdout on real-train
    try:
        y_pred_train = model_obj.predict(X_rt)
        if is_cls:
            train_score = float((y_pred_train == y_rt).mean())
        else:
            from sklearn.metrics import r2_score  # type: ignore
            train_score = float(r2_score(y_rt, y_pred_train))
    except Exception:
        train_score = 0.0

    try:
        y_pred = model_obj.predict(X_re)
        if is_cls:
            real_test_score = float((y_pred == y_re).mean())
            # Build confusion matrix small utility
            labels = np.unique(y_re)
            cm = np.zeros((len(labels), len(labels)), dtype=int)
            lab_to_idx = {lab: i for i, lab in enumerate(labels)}
            for yt, yp in zip(y_re, y_pred):
                cm[lab_to_idx.get(yt, 0), lab_to_idx.get(yp, 0)] += 1
            confusion = cm.tolist()
        else:
            from sklearn.metrics import mean_squared_error  # type: ignore
            real_test_score = float(-mean_squared_error(y_re, y_pred) ** 0.5)
            confusion = None
    except Exception:
        real_test_score = 0.0
        confusion = None

    delta = float(real_test_score - train_score)
    return {
        "synthetic_train_score": train_score,
        "real_test_score": real_test_score,
        "delta": delta,
        "confusion_matrix": confusion,
        "execution_time_seconds": float(time.time() - t0),
        "is_classification": is_cls,
        "preprocess_info": info,
    }


