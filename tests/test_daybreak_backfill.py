from __future__ import annotations

from scripts.backfill_daybreak_programs import changes, historical_program


def test_historical_backfill_only_labels_known_subscription_models():
    assert (
        historical_program("openai_codex", "gpt-daybreak-red-latest") == "daybreak_red"
    )
    assert historical_program("openai_chatgpt_plan", "gpt-6-sol") == "daybreak_blue"
    assert historical_program("openai_compatible", "gpt-6-sol") is None
    assert historical_program("openai", "minimax-m2.5") is None
    assert historical_program("openai_codex", "unknown-model") is None


def test_historical_backfill_preserves_existing_programs():
    usage, changed = changes(
        {
            "gpt-6-sol": {
                "provider": "openai_codex",
                "input": 10,
                "daybreak_programs": ["daybreak_red"],
            },
            "gpt-daybreak-red-latest": {
                "provider": "openai_codex",
                "output": 20,
            },
            "qwen": {"provider": "openai_compatible", "input": 10},
        }
    )
    assert changed
    assert usage["gpt-6-sol"]["daybreak_programs"] == ["daybreak_red"]
    assert usage["gpt-daybreak-red-latest"]["daybreak_programs"] == ["daybreak_red"]
    assert "daybreak_programs" not in usage["qwen"]
