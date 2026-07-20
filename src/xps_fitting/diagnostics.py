"""Residual diagnostics and warning generation."""

from __future__ import annotations

import numpy as np


def statistics(residual: np.ndarray, n_parameters: int) -> dict[str, float]:
    n = residual.size
    rss = float(residual @ residual)
    dof = n - n_parameters
    safe = max(rss / n, np.finfo(float).tiny)
    aic = n * np.log(safe) + 2 * n_parameters
    aicc = aic + (2 * n_parameters * (n_parameters + 1) / (n - n_parameters - 1) if n > n_parameters + 1 else np.inf)
    bic = n * np.log(safe) + n_parameters * np.log(n)
    dw = float(np.diff(residual) @ np.diff(residual) / rss) if rss else 0.0
    signs = residual >= 0
    runs = int(1 + np.count_nonzero(signs[1:] != signs[:-1])) if n else 0
    return {"rss": rss, "reduced_chi_square": rss / dof if dof > 0 else np.nan, "aic": float(aic), "aicc": float(aicc), "bic": float(bic), "durbin_watson": dw, "residual_runs": float(runs), "n_parameters": float(n_parameters), "n_points": float(n)}
