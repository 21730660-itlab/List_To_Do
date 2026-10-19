import pytest

from netops_desk import subnet


def test_calculate_26():
    info = subnet.calculate("192.168.10.37/26")
    assert info["network"] == "192.168.10.0/26"
    assert info["broadcast"] == "192.168.10.63"
    assert (info["first_host"], info["last_host"]) == ("192.168.10.1", "192.168.10.62")
    assert info["usable_hosts"] == 62
    assert info["wildcard"] == "0.0.0.63"
    assert info["scope"] == "Private" and info["ip_class"] == "C"


def test_point_to_point():
    assert subnet.calculate("10.0.0.0/31")["usable_hosts"] == 2


def test_split():
    rows = subnet.split("10.0.0.0/24", 26)
    assert [r["subnet"] for r in rows] == ["10.0.0.0/26", "10.0.0.64/26", "10.0.0.128/26", "10.0.0.192/26"]
    with pytest.raises(ValueError):
        subnet.split("10.0.0.0/24", 20)


def test_invalid():
    with pytest.raises(ValueError):
        subnet.calculate("300.1.1.1/24")
