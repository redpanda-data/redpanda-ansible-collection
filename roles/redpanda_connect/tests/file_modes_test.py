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

COPY_HOSTNAME = 'modenode'
GEN_HOSTNAME = 'modegennode'

MOCK_OPENSSL = """\
#!/bin/bash
out=""
prev=""
for a in "$@"; do
  if [ "$prev" = "-out" ]; then out="$a"; fi
  prev="$a"
done
if [ -n "$out" ]; then touch "$out"; fi
"""


def mode_of(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def base_extravars(hostname, sources):
    # bare include_tasks does not load role defaults
    return {
        'ansible_hostname': hostname,
        'redpanda_user': 'redpanda',
        'redpanda_group': 'redpanda',
        'redpanda_certs_dir': '/etc/redpanda/certs',
        'redpanda_truststore_file': '/etc/redpanda/certs/truststore.pem',
        'redpanda_cert_file': '/etc/redpanda/certs/node.crt',
        'redpanda_key_file': '/etc/redpanda/certs/node.key',
        'ca_cert_file': sources['ca.crt'],
        'node_cert_file': sources['node.crt'],
        'node_key_file': sources['node.key'],
        'overwrite_certs': True,
        'handle_cert_install': True,
        'redpanda_truststores_dir': '/etc/redpanda/truststores',
        'truststore_file_name': 'truststore.p12',
        'redpanda_keystores_dir': '/etc/redpanda/keystores',
        'keystores_file_name': 'keystore.p12',
        'ssl_keystore_type': 'PKCS12',
        'ssl_keystore_location': '/etc/redpanda/keystores/keystore.p12',
        'ssl_keystore_password': 'testpassword',
    }


@pytest.fixture(scope='module')
def deployed():
    work_dir = tempfile.mkdtemp()

    inv = os.path.join(work_dir, 'inventory')
    with open(inv, 'w') as f:
        f.write(INVENTORY)

    mock_path = os.path.join(work_dir, 'openssl')
    with open(mock_path, 'w') as f:
        f.write(MOCK_OPENSSL)
    os.chmod(mock_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    sources = {}
    for name in ('ca.crt', 'node.crt', 'node.key'):
        path = os.path.join(work_dir, name)
        with open(path, 'w') as f:
            f.write(f"test material for {name}\n")
        sources[name] = path

    # staged truststore and keystore, control-node-relative to the playbook;
    # the generate-branch hostname gets a truststore only, so the keystore
    # stat misses and the generate branch runs
    staged_dir = os.path.join('/app/tests', 'tls', 'certs', COPY_HOSTNAME)
    os.makedirs(staged_dir, exist_ok=True)
    for name in ('truststore.p12', 'keystore.p12'):
        with open(os.path.join(staged_dir, name), 'w') as f:
            f.write(f"staged {name}\n")
    gen_staged_dir = os.path.join('/app/tests', 'tls', 'certs', GEN_HOSTNAME)
    os.makedirs(gen_staged_dir, exist_ok=True)
    with open(os.path.join(gen_staged_dir, 'truststore.p12'), 'w') as f:
        f.write("staged truststore.p12\n")

    envvars = {'PATH': f"{work_dir}:{os.environ.get('PATH', '')}"}

    try:
        # staged keystore present: the copy branch runs
        r_copy = ansible_runner.run(
            playbook='/app/tests/file_modes.yml',
            inventory=inv,
            extravars=base_extravars(COPY_HOSTNAME, sources),
            envvars=envvars,
            quiet=False,
        )
        assert r_copy.status == 'successful', f"copy-branch playbook failed: {r_copy.rc}"

        # no staged keystore for this hostname: the generate branch runs
        gen_extravars = base_extravars(GEN_HOSTNAME, sources)
        gen_keystore = os.path.join(work_dir, 'generated-keystore.p12')
        gen_extravars['ssl_keystore_location'] = gen_keystore
        r_gen = ansible_runner.run(
            playbook='/app/tests/file_modes.yml',
            inventory=inv,
            extravars=gen_extravars,
            envvars=envvars,
            quiet=False,
        )
        assert r_gen.status == 'successful', f"generate-branch playbook failed: {r_gen.rc}"

        yield {'generated_keystore': gen_keystore}
    finally:
        shutil.rmtree('/app/tests/tls', ignore_errors=True)
        shutil.rmtree(work_dir, ignore_errors=True)


class TestInstalledFileModes:

    def test_node_key_not_world_readable(self, deployed):
        assert mode_of('/etc/redpanda/certs/node.key') == 0o600, \
            "TLS private key must be readable only by its owner"

    def test_certs_world_readable_is_fine(self, deployed):
        assert mode_of('/etc/redpanda/certs/node.crt') == 0o644
        assert mode_of('/etc/redpanda/certs/truststore.pem') == 0o644

    def test_copied_truststore_not_world_readable(self, deployed):
        # PKCS12 truststores are commonly password-protected; group-read
        # (redpanda) is the widest acceptable
        assert mode_of('/etc/redpanda/truststores/truststore.p12') == 0o640, \
            "truststore must not be world-readable"

    def test_copied_keystore_not_world_readable(self, deployed):
        assert mode_of('/etc/redpanda/keystores/keystore.p12') == 0o640, \
            "keystore holds the node's private key and must not be world-readable"

    def test_generated_keystore_not_world_readable(self, deployed):
        assert mode_of(deployed['generated_keystore']) == 0o640, \
            "generated keystore holds the node's private key and must not be world-readable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
