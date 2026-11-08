import json
import os
import subprocess
import sys


def run_cli(*args):
    env = dict(os.environ, PYTHONPATH="src", QT_QPA_PLATFORM="offscreen")
    return subprocess.run(
        [sys.executable, "-m", "msviewer", *map(str, args)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
    )


def test_inspect_cli_reports_ms_without_gui(tiny_ms):
    result = run_cli("--inspect", tiny_ms)
    assert result.returncode == 0, result.stderr
    info = json.loads(result.stdout)
    assert info["rows"] == 6
    assert info["ddids"][0]["spw"] == 1


def test_bad_path_returns_error_exit_code(tmp_path):
    result = run_cli("--inspect", tmp_path / "missing")
    assert result.returncode != 0
    assert "Measurement Set" in result.stderr
