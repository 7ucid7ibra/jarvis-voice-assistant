from datetime import datetime

import pytest

from jarvis_assistant.intent_utils import (
    is_multi_domain_request,
    looks_like_home_control_request,
    parse_delay_seconds,
    state_matches_action,
)
from jarvis_assistant.profile_paths import profile_file_paths, remove_profile_files


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("turn off light in 10 seconds", 10),
        ("in 5 mins", 300),
        ("in 2 hours", 7200),
        ("in 30 minutes", 1800),
    ],
)
def test_parse_delay_seconds_relative(text: str, expected: int):
    now = datetime(2026, 2, 22, 12, 0, 0)
    assert parse_delay_seconds(text, now) == expected


def test_parse_delay_seconds_absolute_time_same_day():
    now = datetime(2026, 2, 22, 10, 0, 0)
    assert parse_delay_seconds("at 10:45", now) == 45 * 60


def test_parse_delay_seconds_absolute_time_next_day():
    now = datetime(2026, 2, 22, 23, 50, 0)
    assert parse_delay_seconds("at 10:45", now) == 39300


def test_is_multi_domain_request_detects_multiple_domains():
    entities = [
        {"name": "Kitchen Light", "entity_id": "light.kitchen_light", "domain": "light"},
        {"name": "Kitchen Switch", "entity_id": "switch.kitchen_switch", "domain": "switch"},
    ]
    text = "turn on kitchen_light and kitchen_switch"
    assert is_multi_domain_request(text, entities) is True


def test_is_multi_domain_request_does_not_match_suffix_substring():
    entities = [
        {"name": "Kitchen Light", "entity_id": "light.kitchen_light", "domain": "light"},
        {"name": "Kitchen Switch", "entity_id": "switch.kitchen_switch", "domain": "switch"},
    ]
    text = "turn on kitchen_lightning"
    assert is_multi_domain_request(text, entities) is False


def test_is_multi_domain_request_handles_trailing_space_in_name():
    entities = [
        {"name": "Sonnenblumen Lampe", "entity_id": "light.wiz_tunable_white_58bb25", "domain": "light"},
        {"name": "Fernseher ", "entity_id": "input_boolean.lampe_3", "domain": "input_boolean"},
    ]
    text = "schalte die sonnenblumenlampe aus und den fernseher an"
    assert is_multi_domain_request(text, entities) is True


def test_looks_like_home_control_request_true_for_named_entity():
    entities = [
        {"name": "Tischlampe", "entity_id": "light.tischlampe", "domain": "light"},
    ]
    assert looks_like_home_control_request("Schalte bitte die Tischlampe aus.", entities) is True


def test_looks_like_home_control_request_true_for_entity_id():
    entities = [
        {"name": "Kitchen Light", "entity_id": "light.kitchen_light", "domain": "light"},
    ]
    assert looks_like_home_control_request("turn off light.kitchen_light", entities) is True


def test_looks_like_home_control_request_false_for_small_talk():
    entities = [
        {"name": "Tischlampe", "entity_id": "light.tischlampe", "domain": "light"},
    ]
    assert looks_like_home_control_request("Hey, was geht ab?", entities) is False


def test_state_matches_action_turn_off():
    assert state_matches_action("turn_off", "on", "off") is True
    assert state_matches_action("turn_off", "on", "on") is False


def test_state_matches_action_toggle_unknown_initial():
    assert state_matches_action("toggle", "unknown", "on") is True
    assert state_matches_action("toggle", "unknown", "unknown") is False


def test_state_matches_action_set_value_tolerance():
    assert state_matches_action("set_value", "10", "10.0004", value=10) is True
    assert state_matches_action("set_value", "10", "10.2", value=10) is False


def test_profile_paths_and_cleanup(tmp_path):
    memory_path, history_path = profile_file_paths("bobby", base_dir=str(tmp_path))
    assert memory_path.endswith("memory/memory_bobby.json")
    assert history_path.endswith("history/history_bobby.json")

    tmp_path.joinpath("memory").mkdir()
    tmp_path.joinpath("history").mkdir()
    tmp_path.joinpath("memory", "memory_bobby.json").write_text("{}")
    tmp_path.joinpath("history", "history_bobby.json").write_text("{}")

    result = remove_profile_files("bobby", base_dir=str(tmp_path))
    assert result == {"removed_memory": True, "removed_history": True}
    assert not tmp_path.joinpath("memory", "memory_bobby.json").exists()
    assert not tmp_path.joinpath("history", "history_bobby.json").exists()


def test_profile_cleanup_missing_files_is_safe(tmp_path):
    result = remove_profile_files("missing", base_dir=str(tmp_path))
    assert result == {"removed_memory": False, "removed_history": False}
