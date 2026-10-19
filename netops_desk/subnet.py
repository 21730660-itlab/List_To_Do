"""IPv4 subnet calculations used by the Subnet Tool page."""

from __future__ import annotations

import ipaddress


def calculate(cidr: str) -> dict:
    """Describe the network that ``cidr`` (e.g. ``192.168.1.10/24``) belongs to."""
    cidr = cidr.strip()
    if "/" not in cidr:
        cidr += "/32"
    iface = ipaddress.IPv4Interface(cidr)
    net = iface.network
    prefix = net.prefixlen
    if prefix >= 31:
        first, last, usable = net.network_address, net.broadcast_address, net.num_addresses
    else:
        first, last, usable = net.network_address + 1, net.broadcast_address - 1, net.num_addresses - 2
    first_octet = int(str(net.network_address).split(".")[0])
    ip_class = ("A" if first_octet < 128 else "B" if first_octet < 192 else
                "C" if first_octet < 224 else "D (multicast)" if first_octet < 240 else "E")
    return {
        "address": str(iface.ip),
        "network": f"{net.network_address}/{prefix}",
        "netmask": str(net.netmask),
        "wildcard": str(net.hostmask),
        "broadcast": str(net.broadcast_address),
        "first_host": str(first),
        "last_host": str(last),
        "usable_hosts": usable,
        "total_addresses": net.num_addresses,
        "ip_class": ip_class,
        "scope": "Private" if iface.ip.is_private else "Public",
        "binary_mask": ".".join(f"{int(o):08b}" for o in str(net.netmask).split(".")),
    }


def split(cidr: str, new_prefix: int, limit: int = 256) -> list[dict]:
    """Split the network of ``cidr`` into subnets of ``new_prefix``."""
    net = ipaddress.IPv4Interface(cidr.strip()).network
    if new_prefix < net.prefixlen or new_prefix > 32:
        raise ValueError(f"New prefix must be between /{net.prefixlen} and /32")
    result = []
    for i, sub in enumerate(net.subnets(new_prefix=new_prefix)):
        if i >= limit:
            break
        hosts = sub.num_addresses - 2 if new_prefix < 31 else sub.num_addresses
        result.append({
            "subnet": str(sub),
            "range": f"{sub.network_address} - {sub.broadcast_address}",
            "usable_hosts": hosts,
        })
    return result


def format_report(info: dict) -> str:
    rows = [
        ("Address", info["address"]), ("Network", info["network"]),
        ("Netmask", info["netmask"]), ("Wildcard", info["wildcard"]),
        ("Broadcast", info["broadcast"]),
        ("Host range", f"{info['first_host']} - {info['last_host']}"),
        ("Usable hosts", f"{info['usable_hosts']:,}"), ("Class", info["ip_class"]),
        ("Scope", info["scope"]), ("Binary mask", info["binary_mask"]),
    ]
    return "\n".join(f"{k:<13}: {v}" for k, v in rows)
