"""Labels and compact statistical annotations."""

from __future__ import annotations

from ..result import FitResult

PDI_H_C1S_LABELS = {
    "aromatic_C-C_C=C": "aromatic C-C/C=C",
    "C-N_C-Cl": "C-N/C-Cl",
    "imide_N-C=O": "imide N-C=O",
    "acid_O-C=O": "carboxylic O-C=O",
    "pi-pi_star": r"$\pi$-$\pi^*$ satellite",
}


def statistics_text(result: FitResult) -> str:
    parts = []
    for key, label in (("aicc", "AICc"), ("bic", "BIC"), ("reduced_chi_square", r"$\chi_\nu^2$")):
        if key in result.fit_statistics:
            parts.append(f"{label} = {result.fit_statistics[key]:.3g}")
    return "\n".join(parts)
