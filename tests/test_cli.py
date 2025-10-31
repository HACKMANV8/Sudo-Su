import subprocess
import sys


def test_cli_smoke_runs_passes():
    cmd = [sys.executable, "-m", "cli", "smoke"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    assert out.returncode == 0
    assert "SMOKE: PASS" in out.stdout


