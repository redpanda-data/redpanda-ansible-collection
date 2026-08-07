import os
import stat
import tempfile

import pytest
import ansible_runner


# Everything that talks to systemd/rpk or needs a cluster stays skipped; the
# untagged config-generation tasks plus the first-run config write and
# bootstrap write run for real so we can stat their output.
SKIP_TAGS = ','.join([
    'broker_bootstrap_superuser',
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


def mode_of(path):
    return stat.S_IMODE(os.stat(path).st_mode)


@pytest.fixture(scope='module')
def deployed():
    inv = '/app/tests/inventory'
    with open(inv, 'w') as f:
        f.write(INVENTORY)

    src_dir = tempfile.mkdtemp()
    sources = {}
    for name in ('ca.crt', 'node.crt', 'node.key'):
        path = os.path.join(src_dir, name)
        with open(path, 'w') as f:
            f.write(f"test material for {name}\n")
        sources[name] = path

    r = ansible_runner.run(
        playbook='/app/tests/file_modes.yml',
        inventory=inv,
        extravars={
            'ca_cert_file': sources['ca.crt'],
            'node_cert_file': sources['node.crt'],
            'node_key_file': sources['node.key'],
            'overwrite_certs': True,
        },
        cmdline=f'--skip-tags {SKIP_TAGS}',
        quiet=False
    )
    assert r.status == 'successful', f"Playbook failed: {r.rc}"
    return r


class TestInstalledFileModes:

    def test_node_key_not_world_readable(self, deployed):
        assert mode_of('/etc/redpanda/certs/node.key') == 0o600, \
            "TLS private key must be readable only by its owner"

    def test_certs_world_readable_is_fine(self, deployed):
        assert mode_of('/etc/redpanda/certs/node.crt') == 0o644
        assert mode_of('/etc/redpanda/certs/truststore.pem') == 0o644

    def test_node_config_not_world_readable(self, deployed):
        # redpanda.yaml carries rpk.pass and service-account passwords when
        # SASL is enabled; group-read (redpanda) is the widest acceptable
        assert mode_of('/etc/redpanda/redpanda.yaml') == 0o640, \
            "node config may carry SASL credentials and must not be world-readable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
