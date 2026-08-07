import os
import shutil
import stat
import tempfile

import pytest
import ansible_runner


# The inventory host executes locally but with the module working directory
# forced to the remote user's home (see connection_plugins/homedir_local.py),
# which is what a real ssh remote gives tasks. A pre-built keystore staged on
# the control node relative to the playbook directory is therefore invisible
# to any task that resolves the control-node-relative path on the remote.
INVENTORY = """\
[connect]
node1 ansible_connection=homedir_local
"""

HOSTNAME = 'srcnode'

# Records every invocation so tests can assert openssl was never reached.
MOCK_OPENSSL = """\
#!/bin/bash
echo "$@" >> {log}
out=""
prev=""
for a in "$@"; do
  if [ "$prev" = "-out" ]; then out="$a"; fi
  prev="$a"
done
if [ -n "$out" ]; then touch "$out"; fi
"""


def write_mock_openssl(mock_dir):
    log = os.path.join(mock_dir, 'openssl-invocations.log')
    path = os.path.join(mock_dir, 'openssl')
    with open(path, 'w') as f:
        f.write(MOCK_OPENSSL.format(log=log))
    os.chmod(path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    return log


def base_extravars():
    # copy-keystore.yml is included bare, so role defaults are not loaded.
    return {
        'ansible_hostname': HOSTNAME,
        'redpanda_user': 'redpanda',
        'redpanda_group': 'redpanda',
        'keystores_file_name': 'keystore.p12',
        'redpanda_keystores_dir': '/etc/redpanda/keystores',
        'ssl_keystore_type': 'PKCS12',
        'ssl_keystore_location': '/etc/redpanda/keystores/keystore.p12',
        'ssl_keystore_password': 'testpassword',
        'redpanda_cert_file': '/etc/redpanda/certs/node.crt',
        'redpanda_key_file': '/etc/redpanda/certs/node.key',
    }


def task_outcomes(r):
    outcomes = {}
    for event in r.events:
        task = event.get('event_data', {}).get('task', '')
        if event['event'] == 'runner_on_ok':
            outcomes[task] = 'ok'
        elif event['event'] == 'runner_on_skipped':
            outcomes[task] = 'skipped'
        elif event['event'] == 'runner_on_failed':
            outcomes[task] = 'failed'
    return outcomes


class TestKeystoreSourceDetection:

    def test_staged_keystore_is_copied_not_regenerated(self):
        """A keystore staged on the control node must be copied to the host.

        keystores_file is a control-node-relative path; the stat deciding
        copy-vs-generate must therefore run on the control node. If it runs
        on the remote it resolves against the remote home, misses the staged
        file, and a self-signed keystore silently replaces the real one on
        every run.
        """
        staged_dir = os.path.join('/app/tests', 'tls', 'certs', HOSTNAME)
        os.makedirs(staged_dir, exist_ok=True)
        with open(os.path.join(staged_dir, 'keystore.p12'), 'w') as f:
            f.write('prebuilt keystore material\n')

        mock_dir = tempfile.mkdtemp()
        write_mock_openssl(mock_dir)
        inv = os.path.join(mock_dir, 'inventory')
        with open(inv, 'w') as f:
            f.write(INVENTORY)

        try:
            r = ansible_runner.run(
                playbook='/app/tests/copy_keystore.yml',
                inventory=inv,
                extravars=base_extravars(),
                envvars={
                    'ANSIBLE_CONNECTION_PLUGINS': '/app/tests/connection_plugins',
                    'PATH': f"{mock_dir}:{os.environ.get('PATH', '')}",
                },
                quiet=False,
            )

            assert r.status == 'successful', f"Playbook failed: {r.rc}"

            outcomes = task_outcomes(r)
            copy_task = 'Copy keystore to remote hosts in connect group'
            generate_task = 'Create the keystore with a self-signed certificate'

            assert outcomes.get(copy_task) == 'ok', \
                f"staged keystore must be copied, got {outcomes.get(copy_task)!r} (outcomes: {outcomes})"
            assert outcomes.get(generate_task) == 'skipped', \
                f"self-signed generation must be skipped when a keystore is staged, got {outcomes.get(generate_task)!r}"

            with open('/etc/redpanda/keystores/keystore.p12') as f:
                assert f.read() == 'prebuilt keystore material\n', \
                    "the staged keystore content must land on the host untouched"
        finally:
            shutil.rmtree('/app/tests/tls', ignore_errors=True)
            shutil.rmtree(mock_dir, ignore_errors=True)
            if os.path.exists('/etc/redpanda/keystores/keystore.p12'):
                os.unlink('/etc/redpanda/keystores/keystore.p12')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
