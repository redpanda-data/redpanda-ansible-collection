import os
import tempfile

import stat

import pytest
import ansible_runner


SYSTEMCTL_STUB = '''#!/bin/sh
# minimal systemctl for check-mode probes in the test container
case "$1" in
  show) echo "LoadState=loaded"; echo "ActiveState=active"; echo "SubState=running"; echo "UnitFileState=enabled" ;;
esac
exit 0
'''


ROLE = 'redpanda_connect'


def run_playbook(extravars, check_mode=True):
    inv = '/app/tests/spec_inventory'
    with open(inv, 'w') as f:
        f.write('[redpanda]\nlocalhost ansible_connection=local private_ip=10.0.0.1 advertised_ip=10.0.0.1')

    roles_dir = tempfile.mkdtemp()
    os.symlink('/app', os.path.join(roles_dir, ROLE))
    pb = os.path.join(roles_dir, 'spec.yml')
    with open(pb, 'w') as f:
        f.write("""---
- hosts: localhost
  gather_facts: true
  check_mode: {check_mode}
  tasks:
    - name: Invoke role for validation
      ansible.builtin.include_role:
        name: {ROLE}
""".format(check_mode=str(check_mode).lower(), ROLE=ROLE))

    stub = os.path.join(roles_dir, 'systemctl')
    with open(stub, 'w') as f:
        f.write(SYSTEMCTL_STUB)
    os.chmod(stub, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    r = ansible_runner.run(
        playbook=pb, inventory=inv, extravars=extravars,
        envvars={'ANSIBLE_ROLES_PATH': roles_dir,
                 'PATH': f"{roles_dir}:{os.environ.get('PATH', '')}"},
        quiet=False)
    failure_msg = ''
    for event in r.events:
        if event['event'] == 'runner_on_failed':
            failure_msg = str(event['event_data']['res'])
    return r.status, failure_msg


def test_valid_inputs_pass():
    status, msg = run_playbook({'restart_only': True})
    assert status == 'successful', f"valid inputs must validate: {msg}"


@pytest.mark.parametrize("bad,var", [({'copy_keystore': 'banana'}, 'copy_keystore'), ({'restart_only': 'banana'}, 'restart_only'), ({'use_existing_jvm': 'banana'}, 'use_existing_jvm')])
def test_bad_inputs_fail_with_named_error(bad, var):
    status, msg = run_playbook(dict({'restart_only': True}, **bad))
    assert status == 'failed', f"{bad} must fail validation"
    assert var in msg, f"the error must name {var}: {msg!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
