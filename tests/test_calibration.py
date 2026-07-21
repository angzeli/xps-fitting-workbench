import copy

import matplotlib.pyplot as plt
import numpy as np
import pytest

from xps_fitting import calibrate_sample_binding_energy, load_fit_bundle, save_fit_bundle
from xps_fitting.plotting import plot_xps_fit, validate_result_curves
from xps_fitting.result import FitResult
from xps_fitting.spectrum import Spectrum


def fitted_result(core_level: str, component: str, centre: float, sample: str = "PDI-H-COOH") -> FitResult:
    energy = np.linspace(centre - 3, centre + 3, 61)
    background = np.linspace(4, 6, energy.size)
    main = 20 * np.exp(-(((energy - centre) / 0.7) ** 2))
    partner = 5 * np.exp(-(((energy - centre - 1.6) / 0.9) ** 2))
    components = {component: main, "partner": partner}
    total = background + sum(components.values())
    residual = np.sin(energy) * 0.1
    return FitResult(
        energy,
        total + residual,
        background,
        components,
        total,
        residual,
        {
            f"{component}.centre": centre,
            f"{component}.area": 100.0,
            f"{component}.fwhm": 1.2,
            "partner.centre": centre + 1.6,
            "partner.area": 25.0,
            "partner.fwhm": 1.4,
        },
        parameter_uncertainties={f"{component}.centre": 0.05},
        configuration={
            "region": core_level,
            "peaks": [
                {"label": component, "centre": centre, "centre_bounds": (centre - 0.5, centre + 0.5)},
                {
                    "label": "partner",
                    "centre": centre + 1.6,
                    "centre_bounds": [centre + 1.1, centre + 2.1],
                    "centre_offset_from": [component, 1.6],
                },
            ],
        },
        metadata={"sample_name": sample, "data_origin": "experimental"},
    )


def test_sample_wide_calibration_shifts_every_energy_coordinate_without_mutation(tmp_path) -> None:
    c1s = fitted_result("C 1s", "aromatic_C-C_C=C", 284.4)
    cl2p = fitted_result("Cl 2p", "Cl_2p3/2", 199.8)
    n1s = Spectrum(
        np.linspace(396, 404, 81),
        np.linspace(10, 20, 81),
        region="N 1s",
        sample_name="PDI-H-COOH",
        source_file="N1s Scan.VGD",
        metadata={"data_origin": "experimental"},
        normalised_intensity=np.linspace(0, 1, 81),
    )
    result_before = copy.deepcopy({"C 1s": c1s.to_dict(), "Cl 2p": cl2p.to_dict()})
    n1s_energy_before = n1s.binding_energy.copy()
    n1s_intensity_before = n1s.intensity.copy()
    n1s_normalised_before = n1s.normalised_intensity.copy()

    results, spectra, calibration = calibrate_sample_binding_energy(
        {"C 1s": c1s, "Cl 2p": cl2p}, spectra={"N 1s": n1s}, target_eV=284.8
    )

    assert calibration.offset_eV == pytest.approx(0.4)
    assert calibration.observed_eV == 284.4 and calibration.target_eV == 284.8
    assert c1s.to_dict() == result_before["C 1s"]
    assert cl2p.to_dict() == result_before["Cl 2p"]
    np.testing.assert_array_equal(n1s.binding_energy, n1s_energy_before)
    np.testing.assert_array_equal(n1s.intensity, n1s_intensity_before)

    for original, shifted in ((c1s, results["C 1s"]), (cl2p, results["Cl 2p"])):
        np.testing.assert_allclose(shifted.energy, original.energy + 0.4, rtol=0, atol=1e-12)
        for field in ("raw_intensity", "background", "total_fit", "residual"):
            np.testing.assert_array_equal(getattr(shifted, field), getattr(original, field))
        for label in original.components:
            np.testing.assert_array_equal(shifted.components[label], original.components[label])
        for name, value in original.fitted_parameters.items():
            expected = value + 0.4 if name.endswith(".centre") else value
            assert shifted.fitted_parameters[name] == pytest.approx(expected)
        assert shifted.parameter_uncertainties == original.parameter_uncertainties
        assert shifted.metadata["binding_energy_calibration"] == calibration.to_dict()
        validate_result_curves(shifted)

    assert results["C 1s"].fitted_parameters["aromatic_C-C_C=C.centre"] == pytest.approx(284.8)
    c1s_peaks = results["C 1s"].configuration["peaks"]
    assert c1s_peaks[0]["centre"] == pytest.approx(284.8)
    assert c1s_peaks[0]["centre_bounds"] == pytest.approx((284.3, 285.3))
    assert c1s_peaks[1]["centre_offset_from"] == ["aromatic_C-C_C=C", 1.6]

    figure, axis = plot_xps_fit(results["C 1s"], show_peak_positions=True)
    annotation = next(
        text for text in axis.texts if text.get_gid() == "peak-position:aromatic_C-C_C=C"
    )
    assert annotation.get_text() == "284.8 eV"
    assert annotation._xps_fitted_centre == pytest.approx(284.8)
    plt.close(figure)

    shifted_n1s = spectra["N 1s"]
    np.testing.assert_allclose(shifted_n1s.binding_energy, n1s_energy_before + 0.4, rtol=0, atol=1e-12)
    np.testing.assert_array_equal(shifted_n1s.intensity, n1s_intensity_before)
    np.testing.assert_array_equal(shifted_n1s.normalised_intensity, n1s_normalised_before)
    assert shifted_n1s.source_file == n1s.source_file
    assert shifted_n1s.metadata["binding_energy_calibration"] == calibration.to_dict()

    save_fit_bundle(results["C 1s"], tmp_path / "calibrated.bundle")
    reloaded = load_fit_bundle(tmp_path / "calibrated.bundle")
    np.testing.assert_allclose(reloaded.energy, results["C 1s"].energy, rtol=0, atol=1e-12)
    assert reloaded.fitted_parameters["aromatic_C-C_C=C.centre"] == pytest.approx(284.8)
    assert reloaded.metadata["binding_energy_calibration"] == calibration.to_dict()


def test_calibration_rejects_mixed_samples_and_double_application() -> None:
    c1s = fitted_result("C 1s", "aromatic_C-C_C=C", 284.4)
    other_sample = fitted_result("Cl 2p", "Cl_2p3/2", 199.8, sample="PDI-Me-COOH")
    with pytest.raises(ValueError, match="mixed samples"):
        calibrate_sample_binding_energy({"C 1s": c1s, "Cl 2p": other_sample})

    calibrated, _, _ = calibrate_sample_binding_energy({"C 1s": c1s})
    with pytest.raises(ValueError, match="already present"):
        calibrate_sample_binding_energy(calibrated)


def test_calibration_requires_a_finite_fitted_reference() -> None:
    c1s = fitted_result("C 1s", "aromatic_C-C_C=C", 284.4)
    with pytest.raises(KeyError, match="reference core level"):
        calibrate_sample_binding_energy({"carbon": c1s})
    with pytest.raises(KeyError, match="fitted reference centre"):
        calibrate_sample_binding_energy({"C 1s": c1s}, reference_component="missing")
    with pytest.raises(ValueError, match="target_eV must be finite"):
        calibrate_sample_binding_energy({"C 1s": c1s}, target_eV=float("nan"))
