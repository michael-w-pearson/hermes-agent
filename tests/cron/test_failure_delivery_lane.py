import pytest

from cron import scheduler


def test_success_keeps_normal_delivery(monkeypatch):
    monkeypatch.setattr(
        scheduler,
        "load_config",
        lambda: {"cron": {"error_delivery_target": "telegram:1221479515:36948"}},
    )
    job = {"id": "brief", "deliver": "telegram:1221479515:33169"}

    assert scheduler._job_for_cron_delivery(job, success=True) is job


def test_failure_routes_to_dedicated_error_lane_without_mutating_job(monkeypatch):
    monkeypatch.setattr(
        scheduler,
        "load_config",
        lambda: {"cron": {"error_delivery_target": "telegram:1221479515:36948"}},
    )
    job = {"id": "brief", "deliver": "telegram:1221479515:33169"}

    routed = scheduler._job_for_cron_delivery(job, success=False)

    assert routed["deliver"] == "telegram:1221479515:36948"
    assert job["deliver"] == "telegram:1221479515:33169"


def test_failure_keeps_normal_delivery_when_lane_is_unconfigured(monkeypatch):
    monkeypatch.setattr(scheduler, "load_config", lambda: {})
    job = {"id": "brief", "deliver": "origin"}

    assert scheduler._job_for_cron_delivery(job, success=False) is job


def test_failure_lane_config_read_error_blocks_success_destination(monkeypatch):
    def unreadable_config():
        raise ValueError("secret parser detail")

    monkeypatch.setattr(scheduler, "load_config", unreadable_config)
    job = {"id": "brief", "deliver": "telegram:1221479515:33169"}

    with pytest.raises(
        scheduler.CronFailureDeliveryConfigError,
        match=scheduler.FAILURE_LANE_CONFIG_ERROR,
    ):
        scheduler._job_for_cron_delivery(job, success=False)

    assert job["deliver"] == "telegram:1221479515:33169"


def test_outer_exception_delivers_to_dedicated_error_lane(monkeypatch):
    monkeypatch.setattr(
        scheduler,
        "load_config",
        lambda: {"cron": {"error_delivery_target": "telegram:1221479515:36948"}},
    )
    monkeypatch.setattr(scheduler, "create_execution", lambda *args, **kwargs: {"id": "exec-1"})
    monkeypatch.setattr(scheduler, "claim_dispatch", lambda *args, **kwargs: True)
    monkeypatch.setattr(scheduler, "mark_execution_running", lambda *args, **kwargs: None)
    monkeypatch.setattr(scheduler, "mark_job_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(scheduler, "finish_execution", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        scheduler,
        "run_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider exploded")),
    )
    delivered = []
    monkeypatch.setattr(
        scheduler,
        "_deliver_result",
        lambda job, content, **kwargs: delivered.append((job["deliver"], content)),
    )
    job = {
        "id": "brief",
        "name": "Morning Brief",
        "deliver": "telegram:1221479515:33169",
    }

    assert scheduler.run_one_job(job) is False
    assert delivered == [
        (
            "telegram:1221479515:36948",
            "⚠️ Cron 'Morning Brief' failed: provider exploded",
        )
    ]