from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path("/home/michaelpearson/.hermes/scripts/model-routing-guard.py")
SPEC = importlib.util.spec_from_file_location("model_routing_guard", SCRIPT_PATH)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def test_guard_does_not_read_shared_auth_contents(monkeypatch, tmp_path):
    root = tmp_path / ".hermes"
    worker = root / "profiles" / "workhorse"
    worker.mkdir(parents=True)
    (root / "cron").mkdir()

    (root / "config.yaml").write_text(
        """
model:
  provider: openai-codex
  default: gpt-5.6-sol
agent:
  reasoning_effort: high
delegation:
  provider: openai-codex
  model: gpt-5.6-luna
  reasoning_effort: xhigh
fallback_providers: []
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (worker / "config.yaml").write_text(
        """
model:
  provider: openai-codex
  default: gpt-5.6-luna
agent:
  reasoning_effort: xhigh
fallback_providers: []
mcp_servers:
  michael_gateway: {}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    env_path = worker / ".env"
    env_path.write_text("HERMES_GATEWAY_TOKEN=redacted\n", encoding="utf-8")
    env_path.chmod(0o600)

    auth_target = root / "auth.json"
    auth_target.write_text("secret contents must not be read\n", encoding="utf-8")
    auth_target.chmod(0o600)
    (worker / "auth.json").symlink_to(auth_target)

    (root / "cron" / "jobs.json").write_text('{"jobs": []}\n', encoding="utf-8")

    monkeypatch.setattr(guard, "ROOT", root)
    monkeypatch.setattr(guard, "WORKER", worker)
    monkeypatch.setattr(guard, "JOBS", root / "cron" / "jobs.json")
    monkeypatch.setattr(guard, "ALERT_STATE", root / "cron" / ".guard-state.json")

    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args, **kwargs):
        if path.resolve() == auth_target.resolve():
            raise AssertionError("guard must not read auth.json contents")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert guard.main() == 0
