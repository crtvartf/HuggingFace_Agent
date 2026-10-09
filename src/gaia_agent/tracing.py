"""Optional Arize Phoenix tracing via OpenInference (enabled when PHOENIX_ENDPOINT is set)."""

from gaia_agent.settings import Settings


def setup_tracing(settings: Settings, project: str = "gaia-agent") -> bool:
    if not settings.phoenix_endpoint:
        return False
    from openinference.instrumentation.smolagents import SmolagentsInstrumentor
    from phoenix.otel import register

    provider = register(project_name=project, endpoint=settings.phoenix_endpoint, verbose=False)
    SmolagentsInstrumentor().instrument(tracer_provider=provider)
    return True
