"""Ready-made note templates for common IT & network work."""

from datetime import datetime


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


TEMPLATES = {
    "Incident Report": ("Security", "incident", lambda: f"""INCIDENT REPORT  ({_stamp()})
========================================
Severity      : [ ] P1  [ ] P2  [ ] P3  [ ] P4
Affected      :
Reported by   :
Start time    :
End time      :

SUMMARY
-------

IMPACT
------

TIMELINE
--------
{_stamp()}  -

ROOT CAUSE
----------

RESOLUTION
----------

FOLLOW-UP ACTIONS
-----------------
[ ]
"""),
    "Device Config": ("Network", "device, config", lambda: """DEVICE CONFIGURATION
========================================
Hostname      :
Model / OS    :
Mgmt IP       :
Location/Rack :
Serial        :

INTERFACES
----------
Gi0/0  -
Gi0/1  -

VLANS
-----
VLAN 10  -
VLAN 20  -

ROUTING
-------

CONFIG SNIPPET
--------------
```
!
```
"""),
    "Troubleshooting (OSI)": ("Network", "troubleshooting, osi", lambda: f"""TROUBLESHOOTING LOG  ({_stamp()})
========================================
Problem       :
Device / host :

OSI CHECKLIST
-------------
[ ] L1 Physical     - cable, link lights, power, SFP
[ ] L2 Data Link    - VLAN, MAC table, STP, duplex
[ ] L3 Network      - IP / mask / gateway, ping, traceroute, routes
[ ] L4 Transport    - ports open? firewall / ACL
[ ] L5-7 Application- DNS, service running, logs

COMMANDS RUN
------------
```
ping
tracert
ipconfig /all
```

FINDINGS
--------

FIX
---
"""),
    "Change Request": ("Server", "change", lambda: f"""CHANGE REQUEST  ({_stamp()})
========================================
Change        :
Systems       :
Window        :
Risk          : [ ] Low  [ ] Medium  [ ] High

PLAN
----
1.

ROLLBACK PLAN
-------------
1.

VERIFICATION
------------
[ ]
"""),
    "Meeting Notes": ("General", "meeting", lambda: f"""MEETING NOTES  ({_stamp()})
========================================
Attendees     :
Topic         :

DISCUSSION
----------
-

DECISIONS
---------
-

ACTION ITEMS
------------
[ ]
"""),
    "Study / Lab Notes": ("Study", "lab, study", lambda: f"""LAB / STUDY NOTES  ({_stamp()})
========================================
Topic         :   (e.g. CCNA - OSPF single area)
Source        :

KEY CONCEPTS
------------
-

LAB TOPOLOGY
------------
R1 ---- R2 ---- R3

COMMANDS
--------
```
```

QUESTIONS TO REVIEW
-------------------
?
"""),
}
