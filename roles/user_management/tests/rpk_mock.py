"""Shared helpers for user_management tests.

Provides a PATH-mock `rpk` binary that serves canned JSON for the
read-only `rpk security ... list/describe` commands and records every
invocation to a call log so tests can assert which mutating commands
were (not) run.
"""

import json
import os
import stat
import tempfile

import ansible_runner

MOCK_RPK_TEMPLATE = """#!/bin/bash
FIXDIR="__FIXDIR__"
echo "$*" >> "$FIXDIR/calls.log"
case "$*" in
  *"security user list"*) cat "$FIXDIR/users.json" 2>/dev/null ;;
  *"security role list"*) cat "$FIXDIR/roles.json" 2>/dev/null ;;
  *"security acl list"*) cat "$FIXDIR/acls.json" 2>/dev/null ;;
  *"security role describe"*) cat "$FIXDIR/role_describe_$4.json" 2>/dev/null ;;
esac
exit 0
"""

PLAYBOOK = '/app/tests/user_management_test.yml'
INVENTORY_CONTENT = "[redpanda]\nnode0 ansible_connection=local\n"


def make_mock(users=None, roles=None, acls=None, role_describe=None):
    """Create a temp dir containing the mock rpk and its fixtures.

    Each of users/roles/acls is a python object serialized to JSON, or
    None to make the corresponding rpk command emit empty stdout.
    role_describe is a dict of role name -> describe payload.
    Returns the fixture/mock directory path.
    """
    fixdir = tempfile.mkdtemp(prefix='rpkmock')
    fixtures = {'users.json': users, 'roles.json': roles, 'acls.json': acls}
    for fname, payload in fixtures.items():
        if payload is not None:
            with open(os.path.join(fixdir, fname), 'w') as f:
                json.dump(payload, f)
    for role_name, payload in (role_describe or {}).items():
        with open(os.path.join(fixdir, 'role_describe_%s.json' % role_name), 'w') as f:
            json.dump(payload, f)
    rpk_path = os.path.join(fixdir, 'rpk')
    with open(rpk_path, 'w') as f:
        f.write(MOCK_RPK_TEMPLATE.replace('__FIXDIR__', fixdir))
    os.chmod(rpk_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    return fixdir


def run_role(fixdir, extravars):
    """Run the role's task file with the mock rpk on PATH.

    Returns the ansible_runner Runner object.
    """
    inventory = os.path.join(fixdir, 'inventory')
    with open(inventory, 'w') as f:
        f.write(INVENTORY_CONTENT)
    return ansible_runner.run(
        playbook=PLAYBOOK,
        inventory=inventory,
        extravars=extravars,
        envvars={
            'PATH': '%s:%s' % (fixdir, os.environ.get('PATH', '')),
            # the tasks reference the filters by FQCN, so expose the mounted
            # collection plugins under a synthetic collection layout
            'ANSIBLE_COLLECTIONS_PATH': _collection_root(),
        },
        quiet=False,
    )


def _collection_root():
    """Build an ansible_collections tree exposing the mounted plugins as
    redpanda.cluster so FQCN filter references resolve in the harness."""
    root = '/tmp/synthetic-collections'
    pkg = os.path.join(root, 'ansible_collections', 'redpanda', 'cluster')
    os.makedirs(pkg, exist_ok=True)
    link = os.path.join(pkg, 'plugins')
    if not os.path.islink(link):
        os.symlink('/collection-plugins', link)
    return root


def calls(fixdir):
    """Return the recorded rpk invocations, one command line per entry."""
    log = os.path.join(fixdir, 'calls.log')
    if not os.path.exists(log):
        return []
    with open(log) as f:
        return [line.strip() for line in f if line.strip()]
