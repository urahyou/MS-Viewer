"""Masked numerical reductions, independent of Qt and storage."""

import numpy as np

from .model import PlotData, VisibilityBlock

QUANTITIES = ("Amplitude", "Phase", "Real", "Imaginary")


def _mean(values, valid, axis):
    counts = valid.sum(axis=axis)
    sums = np.where(valid, values, 0).sum(axis=axis)
    result = np.full(sums.shape, np.nan, dtype=np.result_type(sums, float))
    np.divide(sums, counts, out=result, where=counts > 0)
    return result


def prepare_plot(
    block: VisibilityBlock, correlation: int, quantity: str, hide_flags: bool = True
) -> PlotData:
    if not 0 <= correlation < block.values.shape[2]:
        raise ValueError("Correlation index out of range")
    if quantity not in QUANTITIES:
        raise ValueError("Unknown visibility quantity")
    z = block.values[:, :, correlation]
    flags = block.flags[:, :, correlation]
    valid = np.isfinite(z) & (~flags if hide_flags else True)
    if quantity == "Phase":
        valid &= z != 0  # Zero visibility has no defined phase.
    transforms = {
        "Amplitude": np.abs,
        "Phase": lambda a: np.angle(a, deg=True),
        "Real": np.real,
        "Imaginary": np.imag,
    }
    values = transforms[quantity](z)
    image = np.where(valid, values, np.nan).astype(np.float32)
    if quantity == "Phase":
        # Circular mean gives each valid phase equal weight, independent of amplitude.
        phasors = np.exp(1j * np.deg2rad(np.where(valid, values, 0)))
        means = [_mean(phasors, valid, axis) for axis in (0, 1)]
        spectrum, trace = [
            np.where(np.abs(mean) > 1e-12, np.angle(mean, deg=True), np.nan) for mean in means
        ]
    else:
        spectrum = _mean(values, valid, 0)
        trace = _mean(values, valid, 1)
    return PlotData(
        block.frequencies / 1e6,
        block.times - block.times[0],
        spectrum,
        trace,
        image,
        float(flags.mean()),
        quantity,
        "deg" if quantity == "Phase" else block.unit,
    )
