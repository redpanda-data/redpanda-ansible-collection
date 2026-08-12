"""Selecting users/roles/acls by desired state must tolerate items without `state`.

The loop expressions select items whose `state` is undefined plus items
with `state: present`. On current ansible-core, `selectattr('state',
'eq', 'present')` over an item that has no `state` key produces an
undefined marker that poisons the whole loop expression ("can only
concatenate list ... UndefinedMarker"), so the role fails to render its
loops as soon as any item pins a state. The selection must first filter
to items where `state` is defined.
"""

import shutil

import pytest

import rpk_mock


def run_scenario():
    fixdir = rpk_mock.make_mock(
        users=[],
        roles={"roles": []},
        acls={"matches": []},
    )
    extravars = {
        "sasl_admin_username": "admin",
        "sasl_admin_password": "admin-pw",
        "sasl_users": [
            {"username": "alice", "password": "alice-pw"},
            {"username": "bob", "password": "bob-pw", "state": "present"},
            {"username": "carol", "password": "carol-pw", "state": "absent"},
        ],
        "sasl_roles": [],
        "sasl_acls": [],
        "schema_registry_acls": [],
    }
    try:
        r = rpk_mock.run_role(fixdir, extravars)
        return r.status, rpk_mock.calls(fixdir)
    finally:
        shutil.rmtree(fixdir, ignore_errors=True)


class TestStateSelection:

    def test_mixed_state_and_stateless_items_render(self):
        status, calls = run_scenario()
        assert status == 'successful', (
            "role must handle sasl_users mixing stateless and state-pinned items")
        creates = [c for c in calls if 'security user create' in c]
        assert any('alice' in c for c in creates), "stateless user alice should be created"
        assert any('bob' in c for c in creates), "state=present user bob should be created"
        assert not any('carol' in c for c in creates), "state=absent user carol must not be created"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))