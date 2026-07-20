"""Fit a constrained synthetic Cl 2p doublet."""

from pathlib import Path

import numpy as np

from xps_fitting.configuration import FitConfig
from xps_fitting.constraints import cl2p_doublet
from xps_fitting.lineshapes import pseudo_voigt
from xps_fitting.optimiser import fit_spectrum
from xps_fitting.plotting import plot_fit
from xps_fitting.spectrum import Spectrum

x = np.linspace(195, 207, 481)
y = 10 + pseudo_voigt(x, 1000, 200, 1.2, 0.5) + pseudo_voigt(x, 500, 201.6, 1.2, 0.5)
result = fit_spectrum(Spectrum(x, y, region="Cl 2p"), FitConfig("Cl_doublet", "Cl 2p", cl2p_doublet("Cl", 199.8, 900)))
print(result.fit_statistics)
output = Path(__file__).resolve().parents[1] / "outputs"; output.mkdir(exist_ok=True)
plot_fit(result, output / "cl2p_diagnostic.png")
