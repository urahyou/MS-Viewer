from pathlib import Path

import numpy as np
import pytest
from casacore.tables import default_ms, makearrcoldesc, maketabdesc, table


@pytest.fixture
def tiny_ms(tmp_path):
    """Real casacore MS with mixed shapes, unsorted times and independently known values."""
    path = tmp_path / "tiny.ms"
    desc = maketabdesc(makearrcoldesc("DATA", 0j, ndim=2, valuetype="complex"))
    with default_ms(str(path), desc) as ms:
        ms.addrows(6)
        for col, values in {
            "DATA_DESC_ID": [0, 0, 0, 0, 1, 1],
            "ANTENNA1": [0, 0, 0, 1, 0, 0],
            "ANTENNA2": [1, 1, 1, 0, 1, 1],
            "FIELD_ID": [0, 0, 1, 0, 0, 0],
            "SCAN_NUMBER": [1, 1, 2, 1, 1, 1],
            "FLAG_ROW": [False, True, False, False, False, False],
        }.items():
            ms.putcol(col, values)
        ms.putcol("TIME", 5e9 + np.array([30, 10, 20, 40, 10, 20]))
        ms.putcolkeyword("DATA", "QuantumUnits", ["Jy"])
        for row in range(6):
            shape = (3, 2) if row < 4 else (2, 1)
            ms.putcell("DATA", row, np.full(shape, row + 3 + 4j, np.complex64))
            flags = np.zeros(shape, bool)
            if row == 0:
                flags[1, 0] = True
            ms.putcell("FLAG", row, flags)

    def sub(name):
        return table(str(path / name), readonly=False, ack=False)

    with sub("ANTENNA") as t:
        t.addrows(2)
        t.putcol("NAME", ["A", "B"])
    with sub("FIELD") as t:
        t.addrows(2)
        t.putcol("NAME", ["Calibrator", "Target"])
    with sub("DATA_DESCRIPTION") as t:
        t.addrows(2)
        t.putcol("SPECTRAL_WINDOW_ID", [1, 0])
        t.putcol("POLARIZATION_ID", [0, 1])
    with sub("SPECTRAL_WINDOW") as t:
        t.addrows(2)
        for i, freqs in enumerate(([80e6, 81e6], [102e6, 101e6, 100e6])):
            t.putcell("NUM_CHAN", i, len(freqs))
            t.putcell("CHAN_FREQ", i, freqs)
    with sub("POLARIZATION") as t:
        t.addrows(2)
        for i, types in enumerate(([9, 12], [1])):
            t.putcell("NUM_CORR", i, len(types))
            t.putcell("CORR_TYPE", i, types)
    with sub("OBSERVATION") as t:
        t.addrows(1)
        t.putcell("TELESCOPE_NAME", 0, "Test array")
    return Path(path)


@pytest.fixture(autouse=True)
def isolated_language_settings(tmp_path):
    """Use real, isolated settings; tests never overwrite the user's language preference."""
    from PyQt6.QtCore import QSettings

    old_format = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings")
    )
    settings = QSettings("RadioAstronomy", "MSViewer")
    settings.setValue("language", "en")
    settings.sync()
    yield
    QSettings.setDefaultFormat(old_format)
