from types import SimpleNamespace

import yaml

from hermes_cli.profiles import read_profile_meta
from hermes_cli.web_server import _profile_to_dict


def test_read_profile_meta_surfaces_display_name(tmp_path):
    (tmp_path / "profile.yaml").write_text(
        yaml.safe_dump(
            {
                "display_name": "Hermes — Chief of Staff",
                "description": "Primary agent",
                "description_auto": False,
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    meta = read_profile_meta(tmp_path)

    assert meta == {
        "description": "Primary agent",
        "description_auto": False,
        "display_name": "Hermes — Chief of Staff",
    }


def test_profile_api_payload_includes_display_name(tmp_path):
    info = SimpleNamespace(
        name="default",
        path=tmp_path,
        is_default=True,
        display_name="Hermes — Chief of Staff",
    )

    payload = _profile_to_dict(info)

    assert payload["name"] == "default"
    assert payload["display_name"] == "Hermes — Chief of Staff"
