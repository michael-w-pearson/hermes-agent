from cron import scheduler_delivery as delivery


ERROR_TARGET = "telegram:1221479515:36948"
SUCCESS_TARGET = "telegram:1221479515:33169"


def test_success_keeps_normal_delivery_without_reading_failure_config(monkeypatch):
    def unexpected_config_read():
        raise AssertionError("success routing must not read failure config")

    monkeypatch.setattr(delivery._sched, "load_config", unexpected_config_read)
    job = {"id": "brief", "deliver": SUCCESS_TARGET}

    assert delivery._delivery_lane_value(job, for_failure=False) == SUCCESS_TARGET


def test_explicit_failure_deliver_wins_without_reading_global_config(monkeypatch):
    def unexpected_config_read():
        raise AssertionError("explicit failure_deliver must win")

    monkeypatch.setattr(delivery._sched, "load_config", unexpected_config_read)
    job = {
        "id": "brief",
        "deliver": SUCCESS_TARGET,
        "failure_deliver": "local",
    }

    assert delivery._delivery_lane_value(job, for_failure=True) == "local"


def test_failure_uses_global_error_lane_when_job_has_no_override(monkeypatch):
    monkeypatch.setattr(
        delivery._sched,
        "load_config",
        lambda: {"cron": {"error_delivery_target": ERROR_TARGET}},
    )
    job = {"id": "brief", "deliver": SUCCESS_TARGET}

    assert delivery._delivery_lane_value(job, for_failure=True) == ERROR_TARGET
    assert job == {"id": "brief", "deliver": SUCCESS_TARGET}


def test_failure_keeps_normal_delivery_when_global_lane_is_unconfigured(monkeypatch):
    monkeypatch.setattr(delivery._sched, "load_config", lambda: {})
    job = {"id": "brief", "deliver": "origin"}

    assert delivery._delivery_lane_value(job, for_failure=True) == "origin"


def test_failure_lane_config_read_error_fails_closed_to_local(monkeypatch, caplog):
    def unreadable_config():
        raise ValueError("secret parser detail")

    monkeypatch.setattr(delivery._sched, "load_config", unreadable_config)
    job = {"id": "brief", "deliver": SUCCESS_TARGET}

    with caplog.at_level("ERROR"):
        lane = delivery._delivery_lane_value(job, for_failure=True)

    assert lane == "local"
    rendered_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert delivery.FAILURE_LANE_CONFIG_ERROR in rendered_logs
    assert "secret parser detail" not in rendered_logs
    assert job == {"id": "brief", "deliver": SUCCESS_TARGET}


def test_failure_target_resolution_uses_global_error_lane(monkeypatch):
    monkeypatch.setattr(
        delivery._sched,
        "load_config",
        lambda: {"cron": {"error_delivery_target": ERROR_TARGET}},
    )
    job = {"id": "brief", "deliver": SUCCESS_TARGET}

    assert delivery._resolve_delivery_targets(job, for_failure=True) == [
        {
            "platform": "telegram",
            "chat_id": "1221479515",
            "thread_id": "36948",
            "_resolved_from": "explicit",
        }
    ]
