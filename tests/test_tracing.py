from iagent.tracing import phoenix_otlp_endpoint


def test_phoenix_otlp_endpoint_appends_traces_path() -> None:
    assert phoenix_otlp_endpoint("http://localhost:6006") == "http://localhost:6006/v1/traces"


def test_phoenix_otlp_endpoint_does_not_double_path() -> None:
    assert (
        phoenix_otlp_endpoint("http://localhost:6006/v1/traces")
        == "http://localhost:6006/v1/traces"
    )


def test_phoenix_otlp_endpoint_empty() -> None:
    assert phoenix_otlp_endpoint("") is None
    assert phoenix_otlp_endpoint("   ") is None


def test_phoenix_otlp_endpoint_reads_env_when_raw_is_none(monkeypatch) -> None:
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://phoenix:6006/")
    assert phoenix_otlp_endpoint() == "http://phoenix:6006/v1/traces"


def test_phoenix_otlp_endpoint_none_when_env_unset(monkeypatch) -> None:
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    assert phoenix_otlp_endpoint() is None
