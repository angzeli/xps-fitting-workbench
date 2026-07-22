import numpy as np

from xps_fitting.backgrounds import linear, shirley


def test_linear_endpoints_and_shirley_stability() -> None:
    x = np.linspace(0, 10, 101)
    np.testing.assert_allclose(linear(x, 2, 5)[[0, -1]], [2, 5])
    y = 2 + np.exp(-(((x - 5) / 1.2) ** 2))
    first = shirley(y)
    np.testing.assert_allclose(first, shirley(y))
    assert np.all(np.isfinite(first))
    assert first[0] == y[0] and first[-1] == y[-1]
