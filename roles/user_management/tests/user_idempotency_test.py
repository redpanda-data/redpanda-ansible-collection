"""Existing users must be recognized, not re-created.

`rpk security user list --format json` emits a list of objects like
[{"username": "alice"}]. The role must extract the username strings so
that membership checks (`item.username in existing_usernames`) work:
an existing user is not re-created, and update_password takes the
update path instead of the create path.
"""

import shutil

import pytest

import rpk_mock


def run_scenario():
    fixdir = rpk_mock.make_mock(
        users=[{"username": "alice"}],
        roles={"roles": []},
        acls={"matches": []},
    )
    extravars = {
        "sasl_admin_username": "admin",
        "sasl_admin_password": "admin-pw",
        "sasl_users": [
            {"username": "alice", "password": "alice-pw", "update_password": True},
            {"username": "bob", "password": "bob-pw"},
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


class TestUserIdempotency:

    def test_existing_user_not_recreated_and_password_update_fires(self):
        status, calls = run_scenario()
        assert status == 'successful'
        creates = [c for c in calls if 'security user create' in c]
        updates = [c for c in calls if 'security user update' in c]
        assert not any('alice' in c for c in creates), (
            "alice already exists but was re-created: %s" % creates)
        assert any('alice' in c for c in updates), (
            "update_password=true should trigger a password update for alice; updates seen: %s" % updates)
        assert any('bob' in c for c in creates), (
            "bob does not exist and should have been created; creates seen: %s" % creates)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))