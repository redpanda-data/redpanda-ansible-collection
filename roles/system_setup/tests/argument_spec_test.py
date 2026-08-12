import os
import tempfile

import pytest
import ansible_runner


ROLE = 'system_setup'


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

    r = ansible_runner.run(
        playbook=pb, inventory=inv, extravars=extravars,
        envvars={'ANSIBLE_ROLES_PATH': roles_dir}, quiet=False)
    failure_msg = ''
    for event in r.events:
        if event['event'] == 'runner_on_failed':
            failure_msg = str(event['event_data']['res'])
    return r.status, failure_msg


def test_valid_inputs_pass():
    status, msg = run_playbook({'prep_data_dir': False, 'data_dir_perms': False, 'ansible_python_interpreter': '/usr/bin/python3'})
    assert status == 'successful', f"valid inputs must validate: {msg}"


@pytest.mark.parametrize("bad,var", [({'prep_data_dir': 'banana'}, 'prep_data_dir'), ({'allow_unmounted_data_dir': 'banana'}, 'allow_unmounted_data_dir'), ({'create_pkg_mgr_proxy': 'banana'}, 'create_pkg_mgr_proxy')])
def test_bad_inputs_fail_with_named_error(bad, var):
    status, msg = run_playbook(dict({'prep_data_dir': False, 'data_dir_perms': False, 'ansible_python_interpreter': '/usr/bin/python3'}, **bad))
    assert status == 'failed', f"{bad} must fail validation"
    assert var in msg, f"the error must name {var}: {msg!r}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))