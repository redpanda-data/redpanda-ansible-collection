import os
import stat
import tempfile

import pytest
import ansible_runner

import rpk_mock


ROLE = 'user_management'

# empty cluster state for every rpk list call; creation loops are empty by
# default so the role is a no-op
MOCK_RPK = """#!/bin/sh
echo '[]'
exit 0
"""


def run_playbook(extravars):
    inv = '/app/tests/spec_inventory'
    with open(inv, 'w') as f:
        f.write('[redpanda]\nlocalhost ansible_connection=local private_ip=10.0.0.1')

    roles_dir = tempfile.mkdtemp()
    os.symlink('/app', os.path.join(roles_dir, ROLE))
    stub = os.path.join(roles_dir, 'rpk')
    with open(stub, 'w') as f:
        f.write(MOCK_RPK)
    os.chmod(stub, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    pb = os.path.join(roles_dir, 'spec.yml')
    with open(pb, 'w') as f:
        f.write("""---
- hosts: localhost
  gather_facts: false
  tasks:
    - name: Invoke role for validation
      ansible.builtin.include_role:
        name: user_management
""")

    r = ansible_runner.run(
        playbook=pb, inventory=inv, extravars=extravars,
        envvars={'ANSIBLE_ROLES_PATH': roles_dir,
                 'ANSIBLE_COLLECTIONS_PATH': rpk_mock._collection_root(),
                 'PATH': f"{roles_dir}:{os.environ.get('PATH', '')}"},
        quiet=False)
    failure_msg = ''
    for event in r.events:
        if event['event'] == 'runner_on_failed':
            failure_msg = str(event['event_data']['res'])
    return r.status, failure_msg


def test_valid_inputs_pass():
    status, msg = run_playbook({})
    assert status == 'successful', f"valid inputs must validate: {msg}"


@pytest.mark.parametrize("bad,var", [
    ({'sasl_users': 'not-a-list'}, 'sasl_users'),
    ({'sasl_users': [{'password': 'x'}]}, 'username'),
])
def test_bad_inputs_fail_with_named_error(bad, var):
    status, msg = run_playbook(bad)
    assert status == 'failed', f"{bad} must fail validation"
    assert var in msg, f"the error must name {var}: {msg!r}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))