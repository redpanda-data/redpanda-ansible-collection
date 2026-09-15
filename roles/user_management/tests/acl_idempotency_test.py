"""ACL creation and role-member assignment must be idempotent.

Mock rpk reports a state in which every desired user, role, role
membership, and ACL already exists (i.e. the state after a first
converging run). A run against that state must not invoke any mutating
rpk command and must report zero changed tasks.
"""

import shutil

import pytest

import rpk_mock

MUTATING_MARKERS = (
    'user create', 'user update', 'user delete',
    'role create', 'role delete', 'role assign', 'role unassign',
    'acl create', 'acl delete',
)


def run_scenario():
    fixdir = rpk_mock.make_mock(
        users=[{"username": "alice"}],
        roles={"roles": [{"name": "writer"}]},
        acls={"matches": [
            {
                "principal": "User:alice",
                "host": "*",
                "resource_type": "TOPIC",
                "resource_name": "foo",
                "pattern_type": "LITERAL",
                "operation": "READ",
                "permission": "ALLOW",
            },
            {
                "principal": "RedpandaRole:writer",
                "host": "*",
                "resource_type": "TOPIC",
                "resource_name": "bar",
                "pattern_type": "LITERAL",
                "operation": "WRITE",
                "permission": "ALLOW",
            },
        ]},
        role_describe={"writer": {
            "name": "writer",
            "members": [{"name": "alice", "principal_type": "User"}],
        }},
    )
    extravars = {
        "sasl_admin_username": "admin",
        "sasl_admin_password": "admin-pw",
        "sasl_users": [{"username": "alice", "password": "alice-pw"}],
        "sasl_roles": [{"name": "writer", "members": ["alice"]}],
        "sasl_acls": [
            {"principal": "User:alice", "operation": "read",
             "resource_type": "topic", "resource_name": "foo"},
            {"role": "writer", "operation": "write",
             "resource_type": "topic", "resource_name": "bar"},
        ],
        "schema_registry_acls": [],
    }
    try:
        r = rpk_mock.run_role(fixdir, extravars)
        changed = (r.stats or {}).get('changed', {})
        return r.status, rpk_mock.calls(fixdir), changed
    finally:
        shutil.rmtree(fixdir, ignore_errors=True)


class TestAclIdempotency:

    def test_converged_state_reports_no_changes(self):
        status, calls, changed = run_scenario()
        assert status == 'successful'
        mutating = [c for c in calls
                    if any(m in c for m in MUTATING_MARKERS)]
        assert mutating == [], (
            "state already converged, but mutating rpk commands ran: %s" % mutating)
        total_changed = sum(changed.values()) if changed else 0
        assert total_changed == 0, (
            "state already converged, but the play reported %d changed tasks" % total_changed)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))