"""Replay real Qt input in a native window; external recording never scans its AX tree.

This developer-only harness tests source code, not a substitute frozen-app stability test.
Run with --output pointing to an ignored artifact directory, then create its 'start' file
once the OS window recorder has begun. No visibility data or flag writes are performed.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from msviewer import window

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("ms", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
window.QSettings = lambda *_: QSettings(str(args.output / "replay.ini"), QSettings.Format.IniFormat)
app = QApplication([sys.argv[0]])
app.setApplicationName("MS Viewer native replay")
w = window.MainWindow()
w.set_language("zh")
w.show()
results = []
state = {"step": 0, "started": False}


def key(widget, value):
    widget.setFocus()
    QTest.keyClick(widget, value)


def run_step():
    try:
        if not state["started"]:
            if not (args.output / "start").exists():
                return
            state["started"] = True
            w.open_ms(args.ms)
            return
        if w._job is not None or w.timer.isActive() or not w._selection_current:
            return
        step = state["step"]
        w.setWindowTitle(f"MS Viewer v0.2.1 · Native QA {step + 1}/7")
        if step == 0:
            w.selection_modes.setCurrentIndex(1)
            QTest.mouseClick(w.query_controls.read_button, Qt.MouseButton.LeftButton)
        elif step == 1:
            w.tabs.setCurrentWidget(w.diagnostic)
            key(w.diagnostic.x_combo, Qt.Key.Key_Down)
            assert w.diagnostic.x_combo.currentData() == "FREQ"
            bounds = w.diagnostic.plot.viewRange()[0]
            assert bounds[0] <= 1350 and bounds[1] >= 1400
            assert "kMHz" not in w.diagnostic.plot.getAxis("bottom").label.toPlainText()
            results.append({"check": "frequency-fit-and-MHz", "range": bounds})
        elif step == 2:
            key(w.diagnostic.y_combo, Qt.Key.Key_Down)
            assert w.diagnostic.y_combo.currentData() == "PHASE"
            bounds = w.diagnostic.plot.viewRange()[1]
            assert bounds[0] < -170 and bounds[1] > 170
            results.append({"check": "phase-fit", "range": bounds})
        elif step == 3:
            key(w.diagnostic.y_combo, Qt.Key.Key_Up)
            QTest.mouseClick(w.diagnostic.region_button, Qt.MouseButton.LeftButton)
            QTest.mouseClick(w.diagnostic.locate_button, Qt.MouseButton.LeftButton)
            assert len(w.inspector.records) > 3
            state["token"] = w._token
            state["first"] = dict(w.inspector.records[0])
        elif step == 4:
            table = w.inspector.table
            QTest.mouseClick(
                table.viewport(),
                Qt.MouseButton.LeftButton,
                pos=table.visualItemRect(table.item(2, 1)).center(),
            )
            selected = table.currentRow()
            assert selected == 2
            record = w.inspector.records[selected]
            assert f"Channel {record['channel']}" in w.inspector.details.toPlainText()
            assert record["correlation"] in w.inspector.details.toPlainText()
            assert w._token == state["token"] and not w.timer.isActive()
            results.append(
                {
                    "check": "clicked-source-record",
                    "row": record["row"],
                    "channel": record["channel"],
                    "correlation": record["correlation"],
                    "locate_total": w.inspector.total,
                    "retained": len(w.inspector.records),
                }
            )
        elif step == 5:
            w.language_actions["en"].trigger()
            assert w.inspector.table.currentRow() == 2
            assert w._token == state["token"]
            results.append({"check": "translation-preserves-record"})
        elif step == 6:
            w.language_actions["zh"].trigger()
            w.tabs.setCurrentWidget(w.antenna_map)
            assert w.antenna_map.baseline is not None
            results.append({"check": "antenna-link", "baseline": w.antenna_map.baseline})
            (args.output / "results.json").write_text(json.dumps(results, indent=2))
            print("PASS " + json.dumps(results), flush=True)
            timer.stop()
            QTimer.singleShot(30000, w.close)
            return
        state["step"] += 1
    except (AssertionError, RuntimeError, ValueError, IndexError, KeyError) as exc:
        (args.output / "failure.txt").write_text(repr(exc))
        print("FAIL " + repr(exc), flush=True)
        timer.stop()
        QTimer.singleShot(1000, w.close)


timer = QTimer()
timer.setInterval(3000)
timer.timeout.connect(run_step)
timer.start()
print(f"READY pid={os.getpid()}", flush=True)
app.exec()
if (args.output / "failure.txt").exists():
    raise SystemExit(1)
if not (args.output / "results.json").exists():
    raise SystemExit("Replay ended before completion")
