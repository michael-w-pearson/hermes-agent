"""Global failure-notice lane: ``cron.error_delivery_target`` for jobs without ``failure_deliver``."""

from __future__ import annotations

import logging

logger = logging.getLogger("cron.scheduler")

FAILURE_LANE_CONFIG_ERROR = (
    "Cron failure-delivery target lookup failed; refusing fallback to the "
    "job's normal delivery destination."
)


def global_failure_target() -> str:
    """Return ``cron.error_delivery_target``, or "" when it is unset. If the config cannot be
    read, return ``local``: a failure notice must not fall back to the job's normal lane."""
    from cron import scheduler as _sched  # late-bound so tests can patch load_config

    try:
        cfg = _sched.load_config() or {}
        return str(((cfg.get("cron") or {}).get("error_delivery_target") or "")).strip()
    except Exception:  # health: allow BLE001 -- fail closed to local; delivery routing must not wedge run bookkeeping, and a config-parse traceback can echo config contents into scheduler logs
        logger.error(FAILURE_LANE_CONFIG_ERROR)
        return "local"
