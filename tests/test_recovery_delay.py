import pytest

from services.recovery_delay import get_recovery_delay


@pytest.mark.parametrize(
    "tag, expected",
    [
        ("price_high", 300),
        ("shipping", 120),
        ("delivery", 120),
        ("unknown_tag", 180),
        (None, 180),
    ],
)
def test_default_mapping(tag, expected):
    assert get_recovery_delay(tag) == expected


def test_custom_override():
    cfg = {"recovery_delays": {"shipping": 999}}
    assert get_recovery_delay("shipping", store_config=cfg) == 999


def test_unknown_custom_falls_back():
    cfg = {"recovery_delays": {"foo": 1}}
    assert get_recovery_delay("shipping", store_config=cfg) == 120
