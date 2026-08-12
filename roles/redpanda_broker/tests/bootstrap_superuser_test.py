import os
import stat

import pytest
import ansible_runner


# Same skip set as file_modes_test, but broker_bootstrap_superuser runs so
# the bootstrap credentials write is exercised for real.
SKIP_TAGS = ','.join([
    'broker_start_tuner',
    'broker_start_sasl',
    'broker_start_standard',
    'broker_node_id',
    'broker_set_node_id',
    'broker_config_version',
    'broker_set_cluster_config',
    'broker_check_license_file',
    'broker_read_license',
    'broker_copy_license',
    'broker_check_license_status',
    'broker_license_needed',
    'broker_apply_license',
    'broker_remove_license',
    'broker_set_license_string',
    'broker_set_license_path',
    'broker_check_restart',
    'broker_check_restart_noauth',
    'broker_write_config_post',
    'broker_restart_required',
    'broker_safe_restart',
])

INVENTORY = """\
[redpanda]
node1 ansible_connection=local private_ip=10.0.0.1
"""

CONF_PATH = '/etc/redpanda.d/bootstrap-superuser.conf'


class TestBootstrapSuperuser:

    def test_bootstrap_conf_written_on_image_without_redpanda_d(self):
        # The redpanda package may ship /etc/redpanda.d, but the role must
        # not depend on it: on images without the directory the very first
        # SASL bootstrap write fails outright.
        assert not os.path.exists('/etc/redpanda.d')

        inv = '/app/tests/inventory'
        with open(inv, 'w') as f:
            f.write(INVENTORY)

        r = ansible_runner.run(
            playbook='/app/tests/file_modes.yml',
            inventory=inv,
            extravars={
                'ca_cert_file': '/dev/null',
                'node_cert_file': '/dev/null',
                'node_key_file': '',
                'kafka_enable_authorization': True,
                'sasl_superuser_username': 'admin',
                'sasl_superuser_password': 'bootstrap-secret',
            },
            cmdline=f'--skip-tags {SKIP_TAGS}',
            quiet=False
        )
        assert r.status == 'successful', f"Playbook failed: {r.rc}"

        assert os.path.isfile(CONF_PATH), "bootstrap superuser conf must exist"
        assert stat.S_IMODE(os.stat(CONF_PATH).st_mode) == 0o600
        with open(CONF_PATH) as f:
            assert 'admin:bootstrap-secret' in f.read()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))