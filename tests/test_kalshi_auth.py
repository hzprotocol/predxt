from predxt.kalshi.auth import build_kalshi_auth_headers


def test_build_kalshi_auth_headers_from_precomputed_signature():
    headers = build_kalshi_auth_headers(
        {"key_id": "k1", "signature": "sig", "timestamp": "123"}
    )
    assert headers == {
        "KALSHI-ACCESS-KEY": "k1",
        "KALSHI-ACCESS-SIGNATURE": "sig",
        "KALSHI-ACCESS-TIMESTAMP": "123",
    }


def test_build_kalshi_auth_headers_with_private_key(monkeypatch):
    captured = {}

    def _fake_sign(**kwargs):
        captured.update(kwargs)
        return "signed-token"

    monkeypatch.setattr(
        "predxt.kalshi.auth._sign_rsa_pss",
        _fake_sign,
    )
    headers = build_kalshi_auth_headers(
        {
            "key_id": "k1",
            "private_key_pem": "-----BEGIN PRIVATE KEY-----...",
            "timestamp": "1000",
        },
        ws_path="/trade-api/ws/v2",
    )

    assert headers == {
        "KALSHI-ACCESS-KEY": "k1",
        "KALSHI-ACCESS-SIGNATURE": "signed-token",
        "KALSHI-ACCESS-TIMESTAMP": "1000",
    }
    assert captured["message"] == "1000GET/trade-api/ws/v2"


def test_build_kalshi_auth_headers_supports_rest_path_and_method(monkeypatch):
    captured = {}

    def _fake_sign(**kwargs):
        captured.update(kwargs)
        return "signed-token"

    monkeypatch.setattr("predxt.kalshi.auth._sign_rsa_pss", _fake_sign)

    headers = build_kalshi_auth_headers(
        {
            "key_id": "k1",
            "private_key_pem": "-----BEGIN PRIVATE KEY-----...",
            "timestamp": "1000",
        },
        ws_path="/trade-api/v2/markets/KXTEST/orderbook",
        method="GET",
    )

    assert headers["KALSHI-ACCESS-KEY"] == "k1"
    assert captured["message"] == "1000GET/trade-api/v2/markets/KXTEST/orderbook"
