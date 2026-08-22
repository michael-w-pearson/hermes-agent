from __future__ import annotations

import dataclasses
import importlib.util
from pathlib import Path


PLUGIN_PATH = Path("/home/michaelpearson/.hermes/plugins/agora-default-router/__init__.py")
SPEC = importlib.util.spec_from_file_location("agora_default_router", PLUGIN_PATH)
assert SPEC and SPEC.loader
router = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(router)


@dataclasses.dataclass
class Source:
    platform: str = "telegram"
    chat_type: str = "dm"
    chat_id: str = "1221479515"
    thread_id: str = "36948"


@dataclasses.dataclass
class Event:
    source: Source
    text: str = ""


def test_empty_text_is_not_an_explicit_topic_command():
    assert router._is_explicit_topic_command("") is False


def test_image_only_event_routes_from_noticeboard_to_agora():
    event = Event(source=Source(), text="")

    result = router.route_inbound_to_agora(event)

    assert result == {"action": "rewrite", "text": ""}
    assert event.source.thread_id == "26643"


def test_existing_agora_event_is_left_untouched():
    event = Event(source=Source(thread_id="26643"), text="hello")

    assert router.route_inbound_to_agora(event) is None
    assert event.source.thread_id == "26643"
