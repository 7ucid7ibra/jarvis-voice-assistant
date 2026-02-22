import pytest

from jarvis_assistant.utils import extract_json


def test_extract_json_with_json_prefix_line():
    raw = 'json\n{"intent":"home_control","target":"input_boolean.lampe_3","action":"turn_off"}'
    data = extract_json(raw)
    assert data["intent"] == "home_control"
    assert data["action"] == "turn_off"


def test_extract_json_with_text_and_multiple_objects_uses_first():
    raw = (
        "Ich schalte die Sonnenblumenlampe aus und den Fernseher an.\n"
        '{"intent":"home_control","target":"light.wiz_tunable_white_58bb25","action":"turn_off"}\n'
        '{"intent":"home_control","target":"input_boolean.lampe_3","action":"turn_on"}'
    )
    data = extract_json(raw)
    assert data["target"] == "light.wiz_tunable_white_58bb25"
    assert data["action"] == "turn_off"


def test_extract_json_with_fenced_block():
    raw = """```json
{"intent":"refresh_entities","action":"refresh"}
```"""
    data = extract_json(raw)
    assert data["intent"] == "refresh_entities"
    assert data["action"] == "refresh"


def test_extract_json_raises_on_missing_json():
    with pytest.raises(ValueError):
        extract_json("No structured payload here.")
