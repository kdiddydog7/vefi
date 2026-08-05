# SPDX-License-Identifier: GPL-3.0-or-later
"""The API key must never appear in an error message or log line."""
import pytest
import requests

from vefi import settings_store
from vefi.api import marketcheck


def test_redact_strips_api_key():
    assert marketcheck._redact("host/x?api_key=ABC123&y=1") == "host/x?api_key=***&y=1"
    assert marketcheck._redact("...extra?api_key=ABC123") == "...extra?api_key=***"
    assert marketcheck._redact("nothing to redact") == "nothing to redact"


def test_request_network_error_redacts_key(monkeypatch):
    settings_store.save_settings({settings_store.KEY_MARKETCHECK: "SUPERSECRETKEY123"})

    def boom(*args, **kwargs):
        # Mirrors the real failure: requests' message embeds the full URL + key.
        raise requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='mc-api.marketcheck.com', port=443): "
            "Max retries exceeded with url: /v2/listing/car/X/extra"
            "?api_key=SUPERSECRETKEY123 (Caused by NameResolutionError(...))"
        )

    monkeypatch.setattr(marketcheck.requests, "get", boom)

    with pytest.raises(marketcheck.MarketCheckError) as excinfo:
        marketcheck._request("https://mc-api.marketcheck.com/v2/listing/car/X/extra")

    message = str(excinfo.value)
    assert "SUPERSECRETKEY123" not in message
    assert "api_key=***" in message
    # And nothing in the chained cause can surface the key either.
    assert excinfo.value.__cause__ is None
