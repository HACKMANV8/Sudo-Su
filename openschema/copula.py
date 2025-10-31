from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd
from scipy import stats as scistats


def apply_rank_copula(source_df: pd.DataFrame, generated_df: pd.DataFrame, numeric_columns: List[str]) -> pd.DataFrame:
    if not numeric_columns:
        return generated_df
    src = source_df[numeric_columns].apply(pd.to_numeric, errors="coerce").dropna()
    gen = generated_df[numeric_columns].apply(pd.to_numeric, errors="coerce").copy()
    if src.empty or gen.empty:
        return generated_df
    # Target Spearman correlation
    R_s, _ = scistats.spearmanr(src, axis=0)
    if isinstance(R_s, float):
        return generated_df
    R_s = np.asarray(R_s)
    # Convert generated marginals to normal scores
    U = np.zeros_like(gen.to_numpy(), dtype=float)
    for j, col in enumerate(numeric_columns):
        ranks = scistats.rankdata(gen[col].to_numpy(), method="average")
        U[:, j] = (ranks - 0.5) / max(len(ranks), 1)
    X = scistats.norm.ppf(U)
    # Adjust correlation via Cholesky
    try:
        L = np.linalg.cholesky(R_s)
    except np.linalg.LinAlgError:
        # Regularize
        eps = 1e-6
        L = np.linalg.cholesky(R_s + eps * np.eye(R_s.shape[0]))
    Y = X @ L.T
    # Map back to original marginals by re-ranking
    out = gen.copy()
    for j, col in enumerate(numeric_columns):
        order = np.argsort(Y[:, j])
        values = np.sort(gen[col].to_numpy())
        out[col] = values[order.argsort()]
    generated_df[numeric_columns] = out[numeric_columns]
    return generated_df


def ranks_from_array(arr: np.ndarray) -> np.ndarray:
    """Convert array to Spearman ranks (1-indexed)."""
    return scistats.rankdata(arr, method="average")


def ranks_to_gaussian(ranks: np.ndarray) -> np.ndarray:
    """Convert ranks to Gaussian latent via uniform transform then norm.ppf."""
    n = len(ranks)
    if n == 0:
        return ranks
    uniform = (ranks - 0.5) / max(n, 1)
    uniform = np.clip(uniform, 1e-10, 1 - 1e-10)  # Avoid exact 0/1
    return scistats.norm.ppf(uniform)


def fit_gaussian_covariance(latent_matrix: np.ndarray) -> np.ndarray:
    """Compute empirical covariance of Gaussian latent matrix."""
    if latent_matrix.shape[0] < 2:
        return np.eye(latent_matrix.shape[1])
    return np.cov(latent_matrix.T)


def sample_from_gaussian_copula(cov_matrix: np.ndarray, n_samples: int, rng: np.random.Generator) -> np.ndarray:
    """Sample from Gaussian copula using Cholesky decomposition."""
    if cov_matrix.shape[0] == 0:
        return np.zeros((n_samples, 0))
    # Regularize if needed
    try:
        L = np.linalg.cholesky(cov_matrix)
    except np.linalg.LinAlgError:
        eps = 1e-6
        reg_cov = cov_matrix + eps * np.eye(cov_matrix.shape[0])
        L = np.linalg.cholesky(reg_cov)
    # Sample standard normal
    Z = rng.normal(size=(n_samples, cov_matrix.shape[0]))
    return Z @ L.T


def gaussian_to_ranks(latents: np.ndarray) -> np.ndarray:
    """Convert Gaussian latents to ranks via norm.cdf then rank transform."""
    n_samples = latents.shape[0]
    uniform = scistats.norm.cdf(latents)
    uniform = np.clip(uniform, 1e-10, 1 - 1e-10)
    # Convert to ranks (1-indexed)
    ranks = (uniform * (n_samples + 1))
    return ranks


def ranks_to_values(ranks: np.ndarray, empirical_values_by_col: List[np.ndarray]) -> np.ndarray:
    """Map ranks back to real numeric values via empirical quantile mapping.
    
    Args:
        ranks: (n_samples, n_cols) array of ranks
        empirical_values_by_col: List of sorted arrays from reference data
    
    Returns:
        (n_samples, n_cols) array of values interpolated from empirical CDFs
    """
    n_samples, n_cols = ranks.shape
    result = np.zeros_like(ranks, dtype=float)
    for j in range(n_cols):
        ref_vals = empirical_values_by_col[j]
        if len(ref_vals) == 0:
            result[:, j] = 0.0
            continue
        # Normalize ranks to [0, 1]
        normalized_ranks = (ranks[:, j] - 1) / (n_samples - 1) if n_samples > 1 else ranks[:, j] - 1
        normalized_ranks = np.clip(normalized_ranks, 0.0, 1.0)
        # Interpolate from empirical CDF
        quantiles = normalized_ranks * (len(ref_vals) - 1)
        indices = quantiles.astype(int)
        indices = np.clip(indices, 0, len(ref_vals) - 1)
        result[:, j] = ref_vals[indices]
    return result


