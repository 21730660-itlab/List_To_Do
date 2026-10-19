from datetime import date, timedelta

import pytest

from netops_desk.db import Database


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "t.db")
    yield d
    d.close()


def test_task_crud_and_status(db):
    tid = db.add_task("Fix DHCP scope", category="Network", priority="High")
    assert db.get_task(tid)["status"] == "Open"
    db.set_task_status(tid, "Done")
    t = db.get_task(tid)
    assert t["status"] == "Done" and t["completed_at"]
    db.set_task_status(tid, "Open")
    assert db.get_task(tid)["completed_at"] is None
    db.update_task(tid, title="Fix DHCP scope on VLAN 10", due_date="")
    assert db.get_task(tid)["title"].endswith("VLAN 10")
    db.delete_task(tid)
    assert db.get_task(tid) is None


def test_empty_title_rejected(db):
    with pytest.raises(ValueError):
        db.add_task("   ")


def test_task_ordering_and_filters(db):
    db.add_task("low", priority="Low")
    db.add_task("crit", priority="Critical")
    db.add_task("done", priority="Critical", status="Done")
    assert [t["title"] for t in db.list_tasks()] == ["crit", "low", "done"]
    assert [t["title"] for t in db.list_tasks(status="Active")] == ["crit", "low"]
    assert [t["title"] for t in db.list_tasks(search="cri")] == ["crit"]


def test_links_cascade(db):
    tid = db.add_task("Replace switch")
    nid = db.add_note("Switch notes", "model: C9200")
    db.link(tid, nid)
    db.link(tid, nid)  # idempotent
    assert db.get_task(tid)["note_count"] == 1
    assert [n["id"] for n in db.notes_for_task(tid)] == [nid]
    assert [t["id"] for t in db.tasks_for_note(nid)] == [tid]
    db.delete_task(tid)
    assert db.get_note(nid)["task_count"] == 0


def test_notes_search_and_pin(db):
    a = db.add_note("A", "ip route 0.0.0.0", tags="routing")
    db.add_note("B", "nothing")
    db.update_note(a, pinned=True)
    assert db.list_notes()[0]["id"] == a
    assert [n["id"] for n in db.list_notes(search="routing")] == [a]
    assert len(db.list_notes(pinned_only=True)) == 1


def test_stats(db):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    db.add_task("late", due_date=yesterday, priority="Critical")
    db.add_task("finished", status="Done")
    s = db.stats()
    assert (s["overdue"], s["critical"], s["done_today"], s["completion"]) == (1, 1, 1, 0.5)


def test_backup(db, tmp_path):
    db.add_note("keep me")
    db.backup(tmp_path / "copy.db")
    copy = Database(tmp_path / "copy.db")
    assert copy.list_notes()[0]["title"] == "keep me"
    copy.close()
