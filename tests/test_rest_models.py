from predxt import (
    BaseRestClient,
    MarketDetail,
    MarketSummary,
    OrderBookLevel,
    VenueApiError,
    VenueCredentialStatus,
)


def test_rest_models_are_public_imports() -> None:
    summary = MarketSummary(
        venue="venue",
        market_id="market-1",
        title="Will it happen?",
        outcomes=["yes", "no"],
    )
    detail = MarketDetail(
        venue="venue",
        market_id="market-1",
        title="Will it happen?",
        token_ids=["token-1"],
    )
    level = OrderBookLevel(price=0.42, size=10)
    status = VenueCredentialStatus(venue="venue", ok=True, message="ok")

    assert summary.outcomes == ["yes", "no"]
    assert detail.token_ids == ["token-1"]
    assert level.price == 0.42
    assert status.ok is True
    assert issubclass(VenueApiError, RuntimeError)
    assert BaseRestClient.__name__ == "BaseRestClient"
