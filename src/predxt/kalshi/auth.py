from __future__ import annotations

import base64
import time
from typing import Any, Optional, cast


def build_kalshi_auth_headers(
    auth_params: dict[str, Any],
    *,
    ws_path: str = "/trade-api/ws/v2",
) -> dict[str, str]:
    """Build Kalshi websocket auth headers.

    Supported modes:
    - precomputed signature via key_id + signature + timestamp
    - RSA-PSS signing via key_id + private_key_pem (+ optional passphrase/timestamp)
    """
    key_id = auth_params.get("key_id")
    signature = auth_params.get("signature")
    timestamp = auth_params.get("timestamp")

    if key_id and signature and timestamp:
        return {
            "KALSHI-ACCESS-KEY": str(key_id),
            "KALSHI-ACCESS-SIGNATURE": str(signature),
            "KALSHI-ACCESS-TIMESTAMP": str(timestamp),
        }

    private_key_pem = auth_params.get("private_key_pem")
    if not (key_id and private_key_pem):
        return {}

    ts = str(timestamp or int(time.time() * 1000))
    msg = f"{ts}GET{ws_path}"
    signed = _sign_rsa_pss(
        message=msg,
        private_key_pem=str(private_key_pem),
        passphrase=auth_params.get("passphrase"),
    )

    return {
        "KALSHI-ACCESS-KEY": str(key_id),
        "KALSHI-ACCESS-SIGNATURE": signed,
        "KALSHI-ACCESS-TIMESTAMP": ts,
    }


def _sign_rsa_pss(
    *, message: str, private_key_pem: str, passphrase: Optional[str]
) -> str:
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
    except ImportError as exc:  # pragma: no cover - depends on runtime env
        raise RuntimeError(
            "cryptography package is required for Kalshi RSA-PSS signing"
        ) from exc

    pwd = passphrase.encode("utf-8") if passphrase else None
    private_key = cast(
        "RSAPrivateKey",
        serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"), password=pwd
        ),
    )
    signature = private_key.sign(
        message.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")
