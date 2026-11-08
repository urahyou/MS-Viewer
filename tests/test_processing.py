"""Guard against wrong masks, phase averaging and axis order in displayed science data."""

import numpy as np
import pytest


def block(values, flags=None, row_flags=None):
    from msviewer.model import VisibilityBlock

    values = np.asarray(values, dtype=complex)[..., None]
    flags = np.zeros(values.shape, bool) if flags is None else np.asarray(flags)[..., None]
    if row_flags is not None:
        flags |= np.asarray(row_flags)[:, None, None]
    return VisibilityBlock(
        times=np.array([5e9, 5e9 + 10]),
        frequencies=np.array([102e6, 101e6]),
        values=values,
        flags=flags,
        row_ids=np.array([4, 9]),
        total_rows=2,
        time_scale="utc",
        unit="Jy",
    )


def test_masks_flagged_samples_in_curves_without_mutating_input():
    from msviewer.processing import prepare_plot

    source = block([[3 + 4j, 12], [8, 6]], [[False, True], [False, False]])
    plot = prepare_plot(source, 0, "Amplitude", True)
    np.testing.assert_allclose(plot.spectrum, [6.5, 6])
    np.testing.assert_allclose(plot.time_trace, [5, 7])
    assert np.isnan(plot.image[0, 1])
    assert source.values[0, 1, 0] == 12
    assert plot.flag_fraction == 0.25
    np.testing.assert_array_equal(plot.frequency_mhz, [102, 101])


def test_phase_mean_is_circular_across_wrap():
    from msviewer.processing import prepare_plot

    z = np.exp(1j * np.deg2rad([[179, -179], [179, -179]]))
    plot = prepare_plot(block(z), 0, "Phase", True)
    np.testing.assert_allclose(np.abs(plot.time_trace), [180, 180], atol=1e-6)


def test_all_flagged_is_nan_without_runtime_warnings():
    from msviewer.processing import prepare_plot

    with np.errstate(all="raise"):
        plot = prepare_plot(block([[1, 2], [3, 4]], np.ones((2, 2), bool)), 0, "Amplitude", True)
    assert np.isnan(plot.spectrum).all()
    assert np.isnan(plot.time_trace).all()


def test_show_flagged_and_nonfinite_values():
    from msviewer.processing import prepare_plot

    plot = prepare_plot(block([[1, np.nan], [3, 5]], np.ones((2, 2), bool)), 0, "Real", False)
    np.testing.assert_allclose(plot.spectrum, [2, 5])
    assert plot.flag_fraction == 1


@pytest.mark.parametrize("corr,quantity", [(2, "Amplitude"), (-1, "Amplitude"), (0, "Bad")])
def test_invalid_plot_selection_is_rejected(corr, quantity):
    from msviewer.processing import prepare_plot

    with pytest.raises(ValueError):
        prepare_plot(block([[1, 2], [3, 4]]), corr, quantity, True)


def test_phase_of_zero_visibility_is_excluded():
    from msviewer.processing import prepare_plot

    plot = prepare_plot(block([[0, 1j], [0, 1j]]), 0, "Phase", True)
    assert np.isnan(plot.spectrum[0])
    np.testing.assert_allclose(plot.time_trace, [90, 90])


def test_opposite_phases_have_undefined_circular_mean():
    from msviewer.processing import prepare_plot

    plot = prepare_plot(block([[1, -1], [1, -1]]), 0, "Phase", True)
    assert np.isnan(plot.time_trace).all()
