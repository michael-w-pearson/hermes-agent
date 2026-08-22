"""Regressions for Michael's reserved Telegram DM routing lanes.

Human-originated DM messages must enter the Agora before session keying and
outbound metadata capture.  Scheduled reports and incident deliveries use
explicit destinations and do not pass through this inbound normalization.
"""

from types import SimpleNamespace

from hermes_state import SessionDB
from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.platforms.base import MessageEvent, MessageType
from gateway.session import SessionSource

CHAT_ID = "1221479515"
AGORA_ID = "26643"
HERALD_ID = "33169"
NOTICEBOARD_ID = "36948"


def _extra():
    return {
        "dm_topics": [
            {
                "chat_id": CHAT_ID,
                "topics": [
                    {"name": "The Herald's Desk", "thread_id": int(HERALD_ID)},
                    {"name": "The Agora", "thread_id": int(AGORA_ID)},
                    {"name": "The Noticeboard", "thread_id": int(NOTICEBOARD_ID)},
                ],
            }
        ],
        "dm_topic_policy": {
            "default_conversation_thread_id": int(AGORA_ID),
            "report_thread_id": int(HERALD_ID),
            "error_thread_id": int(NOTICEBOARD_ID),
        },
        "channel_prompts": {
            NOTICEBOARD_ID: "INCIDENT PROMPT",
            AGORA_ID: "CONVERSATION PROMPT",
        },
    }


def _source(thread_id: str, *, chat_id: str = CHAT_ID, topic: str | None = None):
    return SessionSource(
        platform=Platform.TELEGRAM,
        user_id=chat_id,
        chat_id=chat_id,
        user_name="Michael",
        chat_type="dm",
        thread_id=thread_id,
        chat_topic=topic,
    )


def _runner(tmp_path, *, extra=None):
    from gateway.run import GatewayRunner

    db = SessionDB(db_path=tmp_path / "state.db")
    db.enable_telegram_topic_mode(chat_id=CHAT_ID, user_id=CHAT_ID)
    db.enable_telegram_topic_mode(chat_id="999", user_id="999")

    runner = object.__new__(GatewayRunner)
    runner._session_db = db
    runner.config = GatewayConfig(
        platforms={
            Platform.TELEGRAM: PlatformConfig(
                enabled=True,
                token="***",
                extra=_extra() if extra is None else extra,
            )
        }
    )
    return runner


def test_noticeboard_human_message_recovers_to_agora_before_keying(tmp_path):
    runner = _runner(tmp_path)
    assert runner._recover_telegram_topic_thread_id(
        _source(NOTICEBOARD_ID, topic="The Noticeboard")
    ) == AGORA_ID


def test_herald_human_message_recovers_to_agora_before_keying(tmp_path):
    runner = _runner(tmp_path)
    assert runner._recover_telegram_topic_thread_id(
        _source(HERALD_ID, topic="The Herald's Desk")
    ) == AGORA_ID


def test_agora_message_is_not_rewritten(tmp_path):
    runner = _runner(tmp_path)
    assert runner._recover_telegram_topic_thread_id(
        _source(AGORA_ID, topic="The Agora")
    ) is None


def test_reserved_policy_is_scoped_to_the_configured_chat(tmp_path):
    runner = _runner(tmp_path)
    assert runner._recover_telegram_topic_thread_id(
        _source(NOTICEBOARD_ID, chat_id="999", topic="The Noticeboard")
    ) is None


def test_missing_reserved_policy_preserves_normal_topic_behavior(tmp_path):
    extra = _extra()
    extra.pop("dm_topic_policy")
    runner = _runner(tmp_path, extra=extra)
    assert runner._recover_telegram_topic_thread_id(
        _source(NOTICEBOARD_ID, topic="The Noticeboard")
    ) is None


def test_adapter_recovery_updates_topic_label_and_prompt():
    """Recovery must not leave a Noticeboard label/prompt on an Agora route."""
    from gateway.platforms.base import BasePlatformAdapter

    class _Adapter(BasePlatformAdapter):
        async def connect(self):
            return True

        async def disconnect(self):
            return None

        async def send(self, *args, **kwargs):
            return None

        async def get_chat_info(self, *args, **kwargs):
            return None

    adapter = object.__new__(_Adapter)
    adapter.config = SimpleNamespace(extra=_extra())
    adapter._topic_recovery_fn = lambda source: AGORA_ID

    event = MessageEvent(
        text="branding discussion",
        message_type=MessageType.TEXT,
        source=_source(NOTICEBOARD_ID, topic="The Noticeboard"),
        auto_skill="incident-only-skill",
        channel_prompt="INCIDENT PROMPT",
    )

    adapter._apply_topic_recovery(event)

    assert event.source.thread_id == AGORA_ID
    assert event.source.chat_topic == "The Agora"
    assert event.auto_skill is None
    assert event.channel_prompt == "CONVERSATION PROMPT"
