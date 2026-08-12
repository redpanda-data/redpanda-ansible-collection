"""No password may appear in play output at default verbosity.

The play is run with sentinel passwords on the admin account and on every
managed user, exercising create, update, and delete paths plus role and
ACL loops. Every ansible-runner event and the full stdout stream are
serialized and searched for the sentinels: none may appear.
"""

import json
import shutil

import pytest

import rpk_mock

ADMIN_SENTINEL = 'LEAKCHECK-ADMIN-c41f7b2d9e'
USER_SENTINEL = 'LEAKCHECK-USER-a83d5f1c6b'


def run_scenario():
    fixdir = rpk_mock.make_mock(
        users=[{"username": "alice"}, {"username": "dave"}],
        roles={"roles": [{"name": "writer"}]},
        acls={"matches": []},
        role_describe={"writer": {"name": "writer", "members": []}},
    )
    extravars = {
        "sasl_admin_username": "admin",
        "sasl_admin_password": ADMIN_SENTINEL,
        "sasl_users": [
            # update path
            {"username": "alice", "password": USER_SENTINEL, "update_password": True},
            # create path
            {"username": "bob", "password": USER_SENTINEL},
            # delete path (password present in the item dict)
            {"username": "dave", "password": USER_SENTINEL, "state": "absent"},
        ],
        "sasl_roles": [{"name": "writer", "members": ["alice"]}],
        "sasl_acls": [
            {"principal": "User:alice", "operation": "read",
             "resource_type": "topic", "resource_name": "foo"},
        ],
        "schema_registry_acls": [],
    }
    try:
        r = rpk_mock.run_role(fixdir, extravars)
        events_blob = json.dumps([e for e in r.events], default=str)
        try:
            stdout_blob = r.stdout.read()
        except Exception:
            stdout_blob = ''
        return r.status, events_blob + stdout_blob
    finally:
        shutil.rmtree(fixdir, ignore_errors=True)


class TestNoSecretLeak:

    def test_sentinel_passwords_never_in_events(self):
        status, blob = run_scenario()
        assert status == 'successful'
        assert USER_SENTINEL not in blob, (
            "a managed user's password leaked into play output")
        assert ADMIN_SENTINEL not in blob, (
            "the admin password leaked into play output")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))