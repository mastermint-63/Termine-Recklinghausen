"""agy läuft nur mit Headless-HOME und im eigenen Anhang-Verzeichnis (Schutz vor Prompt Injection)."""
import json
from types import SimpleNamespace

import pytest

import hw_import


def test_run_agy_hw_setzt_headless_home_und_eigenes_verzeichnis(tmp_path, monkeypatch):
    (tmp_path / ".gemini" / "antigravity-cli").mkdir(parents=True)
    monkeypatch.setenv("AGY_HOME", str(tmp_path))
    aufrufe = []

    def fake_run(cmd, **kwargs):
        aufrufe.append(kwargs)
        return SimpleNamespace(returncode=0, stderr="",
                               stdout=json.dumps({"status": "SUCCESS", "structured_output": {"termine": []}}))

    monkeypatch.setattr(hw_import.subprocess, "run", fake_run)
    assert hw_import._run_agy_hw("Prompt", {}, "gemini-3.8-flash-low", [], []) == {"termine": []}
    assert aufrufe[0]["env"]["HOME"] == str(tmp_path)
    assert aufrufe[0]["cwd"] != "/tmp"


def test_run_agy_hw_bricht_ohne_headless_home_ab(tmp_path, monkeypatch):
    monkeypatch.setenv("AGY_HOME", str(tmp_path / "fehlt"))
    monkeypatch.setattr(hw_import.subprocess, "run", lambda *a, **k: pytest.fail("agy darf nicht starten"))
    with pytest.raises(RuntimeError, match="Headless-HOME"):
        hw_import._run_agy_hw("Prompt", {}, "gemini-3.8-flash-low", [], [])
