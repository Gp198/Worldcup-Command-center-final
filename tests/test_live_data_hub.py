from connectors.live_data import LiveFootballDataHub


def test_live_data_hub_health_has_fallback_provider():
    hub = LiveFootballDataHub()
    health = hub.health()
    assert any(item["provider"] == "Local datasets" for item in health)
