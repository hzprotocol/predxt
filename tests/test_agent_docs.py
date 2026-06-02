from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_llms_docs_reference_supported_public_apis() -> None:
    docs = "\n".join(
        [
            (ROOT / "llms.txt").read_text(encoding="utf-8"),
            (ROOT / "llms-full.txt").read_text(encoding="utf-8"),
            (ROOT / "skills/predxt/SKILL.md").read_text(encoding="utf-8"),
        ]
    )

    for api_name in [
        "PolymarketWsClient",
        "KalshiWsClient",
        "OpinionWsClient",
        "VenueMessage",
        "OrderBookState",
        "typed_event_from_message",
    ]:
        assert api_name in docs


def test_agent_eval_prompts_keep_read_only_contract() -> None:
    prompt_dir = ROOT / "evals/agent_prompts"
    prompts = list(prompt_dir.glob("*.md"))

    assert prompts
    for prompt in prompts:
        text = prompt.read_text(encoding="utf-8").lower()
        assert "read-only" in text
        assert "order placement" in text or "execution" in text
