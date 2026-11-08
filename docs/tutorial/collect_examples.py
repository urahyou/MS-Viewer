"""Read-only, reproducible numerical examples used in the beginner PDF."""
import json
from pathlib import Path

import numpy as np
from casacore.tables import table
from msviewer.model import Selection
from msviewer.processing import prepare_plot
from msviewer.reader import inspect_ms, read_visibility

OUT = Path('tmp/pdfs/guide')
OUT.mkdir(parents=True, exist_ok=True)
arrays = {}
facts = {}
for key, name, selection, quantity in (
    ('sim', 'simulated.ms', Selection(0, 0, 1, field=0), 'Amplitude'),
    ('alma64', 'mssel_test_small.ms', Selection(1, 0, 9, field=1), 'Amplitude'),
    ('alma1', 'mssel_test_small.ms', Selection(2, 0, 9), 'Imaginary'),
    ('field0', 'mssel_test_small.ms', Selection(2, 0, 9, field=0), 'Imaginary'),
    ('field1', 'mssel_test_small.ms', Selection(2, 0, 9, field=1), 'Imaginary'),
):
    meta = inspect_ms(Path('data') / name)
    block = read_visibility(meta.path, selection)
    plot = prepare_plot(block, 0, quantity, True)
    for attribute in ('frequency_mhz', 'elapsed_seconds', 'spectrum', 'time_trace', 'image'):
        arrays[f'{key}_{attribute}'] = getattr(plot, attribute)
    arrays[f'{key}_times'] = block.times
    arrays[f'{key}_flags'] = block.flags[:, :, 0]
    facts[key] = dict(ms=name, ddid=selection.ddid, field=selection.field,
                      baseline=[selection.antenna1, selection.antenna2], shape=list(block.values.shape),
                      flag_fraction=plot.flag_fraction, unit=plot.unit,
                      finite_time_samples=int(np.isfinite(plot.time_trace).sum()),
                      first_finite_seconds=(float(plot.elapsed_seconds[np.flatnonzero(np.isfinite(plot.time_trace))[0]])
                                            if np.isfinite(plot.time_trace).any() else None))
meta = inspect_ms('data/mssel_test_small.ms')
facts['alma_metadata'] = dict(rows=meta.rows, antennas=meta.antennas, fields=meta.fields,
    descriptions=[dict(ddid=d.ddid, spw=d.spw, polarization=d.polarization,
                       correlations=d.correlations, channels=len(d.frequencies),
                       low_mhz=float(d.frequencies.min()/1e6), high_mhz=float(d.frequencies.max()/1e6))
                  for d in meta.descriptions])
with table(str(meta.path), readonly=True, ack=False) as ms:
    facts['alma_metadata']['data_keywords'] = ms.getcolkeywords('DATA')
np.savez(OUT/'examples.npz', **arrays)
(OUT/'facts.json').write_text(json.dumps(facts, ensure_ascii=False, indent=2))
print(json.dumps(facts, ensure_ascii=False, indent=2))
