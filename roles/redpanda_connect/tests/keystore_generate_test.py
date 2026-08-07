import json
import os
import shutil
import stat
import tempfile

import pytest
import ansible_runner


INVENTORY = """\
[connect]
node1 ansible_connection=local
"""

HOSTNAME = 'gennode'

# Records every invocation so tests can count how often openssl really ran,
# and creates the -out file so a generated keystore exists afterwards.
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


def extravars(keystore_location, password):
    # copy-keystore.yml is included bare, so role defaults are not loaded.
    return {
        'ansible_hostname': HOSTNAME,
        'redpanda_user': 'redpanda',
        'redpanda_group': 'redpanda',
        'keystores_file_name': 'keystore.p12',
        'redpanda_keystores_dir': os.path.dirname(keystore_location),
        'ssl_keystore_type': 'PKCS12',
        'ssl_keystore_location': keystore_location,
        'ssl_keystore_password': password,
        'redpanda_cert_file': '/etc/redpanda/certs/node.crt',
        'redpanda_key_file': '/etc/redpanda/certs/node.key',
    }


class KeystoreGenerateRun:
    def __init__(self):
        self.work_dir = tempfile.mkdtemp()
        self.log = os.path.join(self.work_dir, 'openssl-invocations.log')
        mock_path = os.path.join(self.work_dir, 'openssl')
        with open(mock_path, 'w') as f:
            f.write(MOCK_OPENSSL.format(log=self.log))
        os.chmod(mock_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        self.inventory = os.path.join(self.work_dir, 'inventory')
        with open(self.inventory, 'w') as f:
            f.write(INVENTORY)
        self.keystore_dir = os.path.join(self.work_dir, 'keystores')
        self.keystore_location = os.path.join(self.keystore_dir, 'keystore.p12')

    def run(self, password='testpassword'):
        return ansible_runner.run(
            playbook='/app/tests/copy_keystore.yml',
            inventory=self.inventory,
            extravars=extravars(self.keystore_location, password),
            envvars={'PATH': f"{self.work_dir}:{os.environ.get('PATH', '')}"},
            quiet=False,
        )

    def openssl_invocations(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            return f.read().splitlines()

    def cleanup(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)


def generate_task_result(r):
    for event in r.events:
        if event['event'] != 'runner_on_ok':
            continue
        if event.get('event_data', {}).get('task', '') == 'Create the keystore with a self-signed certificate':
            return event['event_data']['res']
    return None


class TestKeystoreGeneration:

    def test_generation_is_idempotent(self):
        """Rerunning the role must not regenerate an existing keystore.

        The generate command needs a creates guard: without it every run
        rewrites the keystore, reports changed, and churns Connect restarts.
        """
        runner = KeystoreGenerateRun()
        try:
            r1 = runner.run()
            assert r1.status == 'successful', f"first run failed: {r1.rc}"
            assert os.path.exists(runner.keystore_location), \
                "the generate branch must produce the keystore"
            assert len(runner.openssl_invocations()) == 1, \
                f"openssl must run exactly once on first run, got {runner.openssl_invocations()}"

            r2 = runner.run()
            assert r2.status == 'successful', f"second run failed: {r2.rc}"
            assert len(runner.openssl_invocations()) == 1, \
                "openssl must not run again while the keystore already exists"
            res = generate_task_result(r2)
            assert res is not None, "generate task must complete ok on the second run"
            # no_log censors the per-task result, so idempotence is asserted
            # via the recap: nothing may report changed on the second run.
            changed = (r2.stats or {}).get('changed', {}).get('node1', 0)
            assert changed == 0, \
                f"second run must report no changes, recap says {changed} changed"
        finally:
            runner.cleanup()

    def test_keystore_password_never_appears_in_events(self):
        """The keystore password must not leak into task output.

        Passing it as a pass:... command argument put it in the recorded
        module invocation (and in ps on the host); the task needs no_log and
        an environment-variable handoff instead.
        """
        sentinel = 'SENTINEL-KEYSTORE-PW-c81d4e2e'
        runner = KeystoreGenerateRun()
        try:
            r = runner.run(password=sentinel)
            assert r.status == 'successful', f"run failed: {r.rc}"
            for event in r.events:
                payload = json.dumps(event, default=str)
                assert sentinel not in payload, \
                    f"keystore password leaked into event {event.get('event')} / task {event.get('event_data', {}).get('task')!r}"
        finally:
            runner.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
