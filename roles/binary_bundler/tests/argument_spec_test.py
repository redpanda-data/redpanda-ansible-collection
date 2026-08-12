import os
import tempfile

import pytest
import ansible_runner


ROLE = 'binary_bundler'


def run_playbook(extravars):
    inv = '/app/tests/spec_inventory'
    with open(inv, 'w') as f:
        f.write('localhost ansible_connection=local')

    roles_dir = tempfile.mkdtemp()
    os.symlink('/app', os.path.join(roles_dir, ROLE))

    # file:// fixtures so the valid case can run the real deb bundle flow
    fixtures = tempfile.mkdtemp()
    for pkg in ('redpanda', 'redpanda-rpk', 'redpanda-tuner'):
        pkg_dir = os.path.join(fixtures, 'apt/pool/main/r', pkg)
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, f'{pkg}_24.3.1-1_amd64.deb'), 'w') as f:
            f.write(f'fixture {pkg}\n')

    pb = os.path.join(roles_dir, 'spec.yml')
    with open(pb, 'w') as f:
        f.write("""---
- hosts: localhost
  gather_facts: false
  tasks:
    - name: Invoke role for validation
      ansible.builtin.include_role:
        name: binary_bundler
""")

    base = {
        'redpanda_version': '24.3.1-1',
        'basearch': 'x86_64',
        'rpm_or_deb': 'deb',
        'redpanda_base_url': f'file://{fixtures}',
        'download_directory': tempfile.mkdtemp(),
    }
    r = ansible_runner.run(
        playbook=pb, inventory=inv, extravars={**base, **extravars},
        envvars={'ANSIBLE_ROLES_PATH': roles_dir}, quiet=False)
    failure_msg = ''
    for event in r.events:
        if event['event'] == 'runner_on_failed':
            failure_msg = str(event['event_data']['res'])
    return r.status, failure_msg


def test_valid_inputs_pass():
    status, msg = run_playbook({})
    assert status == 'successful', f"valid inputs must validate: {msg}"


@pytest.mark.parametrize("bad,var", [
    ({'rpm_or_deb': 'tarball'}, 'rpm_or_deb'),
    ({'is_using_unstable': 'banana'}, 'is_using_unstable'),
])
def test_bad_inputs_fail_with_named_error(bad, var):
    status, msg = run_playbook(bad)
    assert status == 'failed', f"{bad} must fail validation"
    assert var in msg, f"the error must name {var}: {msg!r}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))