"""Fresh clusters can return empty output from rpk list commands.

`from_json` on empty stdout raises a parse error that `| default([])`
cannot catch, so the role hard-fails on a fresh cluster before it has
created anything. The role must treat empty stdout as an empty list and
proceed to create the requested users.
"""

import shutil

import pytest

import rpk_mock


def run_scenario():
    # No fixture files at all: every rpk list command emits empty stdout.
    fixdir = rpk_mock.make_mock()
    extravars = {
        "sasl_admin_username": "admin",
        "sasl_admin_password": "admin-pw",
        "sasl_users": [
            {"username": "carol", "password": "carol-pw"},
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


class TestEmptyState:

    def test_empty_rpk_output_treated_as_empty_state(self):
        status, calls = run_scenario()
        assert status == 'successful', (
            "role must proceed with empty state when rpk emits no output")
        creates = [c for c in calls if 'security user create' in c]
        assert any('carol' in c for c in creates), (
            "carol should have been created on the fresh cluster; creates seen: %s" % creates)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
