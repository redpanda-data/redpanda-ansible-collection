import os
import tempfile

import pytest
import ansible_runner


def run_playbook(extravars):
    # install_certs_only short-circuits main.yml right after role entry, so
    # the argument-spec validation runs for real without any install work
    extravars = {'install_certs_only': True, **extravars}
    inventory_path = '/app/tests/inventory'
    with open(inventory_path, 'w') as f:
        f.write('[redpanda]\nlocalhost ansible_connection=local private_ip=10.0.0.1')

    # the role is mounted at /app; include_role needs it under its real name
    roles_dir = tempfile.mkdtemp()
    os.symlink('/app', os.path.join(roles_dir, 'redpanda_broker'))

    r = ansible_runner.run(
        playbook='/app/tests/argument_spec.yml',
        inventory=inventory_path,
        extravars=extravars,
        envvars={'ANSIBLE_ROLES_PATH': roles_dir},
        quiet=False
    )
    failure_msg = ''
    for event in r.events:
        if event['event'] == 'runner_on_failed':
            failure_msg = str(event['event_data']['res'])
    return r.status, failure_msg


class TestArgumentSpec:

    def test_valid_defaults_pass(self):
        status, msg = run_playbook({})
        assert status == 'successful', f"defaults must validate: {msg}"

    def test_bad_install_status_fails_with_named_error(self):
        status, msg = run_playbook({'redpanda_install_status': 'installed'})
        assert status == 'failed', \
            "an invalid redpanda_install_status must fail validation at entry"
        assert 'redpanda_install_status' in msg

    def test_bad_fips_mode_fails_with_named_error(self):
        status, msg = run_playbook({'fips_mode': 'on'})
        assert status == 'failed', \
            "an invalid fips_mode must fail validation at entry"
        assert 'fips_mode' in msg

    def test_malformed_listener_fails_with_named_error(self):
        status, msg = run_playbook({
            'redpanda_kafka_listeners': [{'address': '10.0.0.1'}],
        })
        assert status == 'failed', \
            "a listener without port/name must fail validation at entry"
        assert 'redpanda_kafka_listeners' in msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
