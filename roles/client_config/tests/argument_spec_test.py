import os
import stat
import tempfile
import zipfile

import pytest
import ansible_runner


ROLE = 'client_config'


def run_playbook(extravars):
    inv = '/app/tests/spec_inventory'
    with open(inv, 'w') as f:
        f.write('localhost ansible_connection=local')

    roles_dir = tempfile.mkdtemp()
    os.symlink('/app', os.path.join(roles_dir, ROLE))

    # file:// fixtures so the real role runs offline: a tiny rpk zip and a
    # CA cert file
    fixtures = tempfile.mkdtemp()
    zip_path = os.path.join(fixtures, 'rpk.zip')
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('rpk', '#!/bin/sh\nexit 0\n')
    with open(os.path.join(fixtures, 'ca.crt'), 'w') as f:
        f.write('test ca material\n')

    pb = os.path.join(roles_dir, 'spec.yml')
    with open(pb, 'w') as f:
        f.write("""---
- hosts: localhost
  gather_facts: true
  vars:
    ansible_python_interpreter: /usr/bin/python3
  tasks:
    - name: Invoke role for validation
      ansible.builtin.include_role:
        name: client_config
""")

    base = {
        'rpk_url': f'file://{zip_path}',
        'cert_src_dir': fixtures,
        'truststore_name': 'ca.crt',
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


# No bad-input cases: every declared option is a plain string and Ansible's
# str type coerces nearly any scalar, so the spec cannot reject values for
# this role -- its worth here is documentation and defaults. The valid-run
# case still proves the spec parses and the role executes under it.


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))