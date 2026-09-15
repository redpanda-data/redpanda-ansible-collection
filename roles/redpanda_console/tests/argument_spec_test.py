import os
import tempfile

import pytest
import ansible_runner


ROLE = 'redpanda_console'


def run_playbook(extravars, check_mode=False):
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
    status, msg = run_playbook({'install_certs_only': True, 'redpanda_version': 'latest'})
    assert status == 'successful', f"valid inputs must validate: {msg}"


@pytest.mark.parametrize("bad,var", [({'enable_airgap': 'banana'}, 'enable_airgap'), ({'handle_cert_install': 'banana'}, 'handle_cert_install'), ({'is_using_unstable': 'banana'}, 'is_using_unstable')])
def test_bad_inputs_fail_with_named_error(bad, var):
    status, msg = run_playbook(dict({'install_certs_only': True, 'redpanda_version': 'latest'}, **bad))
    assert status == 'failed', f"{bad} must fail validation"
    assert var in msg, f"the error must name {var}: {msg!r}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))