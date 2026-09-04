import pytest

import wger_client


@pytest.fixture(autouse=True)
def no_retry_backoff(monkeypatch):
    monkeypatch.setattr(wger_client.time, "sleep", lambda seconds: None)
