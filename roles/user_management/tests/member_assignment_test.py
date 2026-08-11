"""Role member assignment must work for roles without an explicit state.

The assign loop concatenates stateless roles with state=present roles
and pipes the result through subelements to pair each role with its
members. Jinja filters bind tighter than `+`, so subelements was applied
only to the state=present half: stateless roles (the common case)
arrived unpaired and the task crashed resolving `item.0.name`.
"""

import shutil

import pytest

import rpk_mock


def run_scenario():
    fixdir = rpk_mock.make_mock(
        users=[{"username": "alice"}],
        roles={"roles": [{"name": "writer"}]},
        acls={"matches": []},
        role_describe={"writer": {"name": "writer", "members": []}},
    )
    extravars = {
        "sasl_admin_username": "admin",
        "sasl_admin_password": "admin-pw",
        "sasl_users": [{"username": "alice", "password": "alice-pw"}],
        # no state key on the role: must still be paired with its members
        "sasl_roles": [{"name": "writer", "members": ["alice"]}],
        "sasl_acls": [],
        "schema_registry_acls": [],
    }
    try:
        r = rpk_mock.run_role(fixdir, extravars)
        return r.status, rpk_mock.calls(fixdir)
    finally:
        shutil.rmtree(fixdir, ignore_errors=True)


class TestMemberAssignment:

    def test_stateless_role_members_assigned(self):
        status, calls = run_scenario()
        assert status == 'successful', (
            "assigning members of a stateless role must not fail")
        assigns = [c for c in calls if 'role assign' in c]
        assert any('writer' in c and 'User:alice' in c for c in assigns), (
            "alice is not yet a member of writer and should have been assigned; "
            "assigns seen: %s" % assigns)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))