"""Behavioral test for the required-variable guard in install-certs.yml.

install-certs.yml requires ca_cert_file and node_cert_file (node_key_file
stays optional -- the harness's deploy-console-tls playbook omits it),
none of which have defaults. When handle_cert_install is enabled without
them, the play used to die mid-run with a raw Jinja undefined-variable
error after already creating users/directories. The task file must instead
fail up front with an assert whose message names every missing variable.
"""
import os
import tempfile

import pytest
import ansible_runner

PLAYBOOK = '/app/tests/cert_guard.yml'
INVENTORY = '/app/tests/inventory'

CERT_VARS = ('ca_cert_file', 'node_cert_file')


def run(extra_vars):
    with open(INVENTORY, 'w') as f:
        f.write('localhost ansible_connection=local')

    r = ansible_runner.run(
        playbook=PLAYBOOK,
        inventory=INVENTORY,
        extravars=extra_vars,
        quiet=True,
    )

    failures = []
    for event in r.events:
        if event['event'] == 'runner_on_failed':
            data = event.get('event_data', {})
            failures.append((data.get('task', ''),
                             data.get('res', {}).get('msg', '')))
    return r.status, failures


class TestCertVarGuard:

    def test_missing_cert_vars_fail_fast_with_named_variables(self):
        status, failures = run({'handle_cert_install': True})
        assert status == 'failed'
        assert failures, "expected a failing task"
        first_task, first_msg = failures[0]
        for var in CERT_VARS:
            assert var in first_msg, (
                f"the first failure ({first_task!r}) must be an up-front assert "
                f"naming every required variable; {var} is missing from: {first_msg!r}"
            )

    def test_with_cert_vars_defined_play_succeeds(self):
        cert_dir = tempfile.mkdtemp()
        paths = {}
        for var, fname in zip(CERT_VARS, ('ca.crt', 'node.crt', 'node.key')):
            path = os.path.join(cert_dir, fname)
            with open(path, 'w') as f:
                f.write('dummy pem material\n')
            paths[var] = path

        extra = {'handle_cert_install': True}
        extra.update(paths)
        status, failures = run(extra)
        assert status == 'successful', f"unexpected failures: {failures}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
