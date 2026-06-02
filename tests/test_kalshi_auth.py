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
    monkeypatch.setattr(
        "predxt.kalshi.auth._sign_rsa_pss",
        lambda **_kwargs: "signed-token",
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
