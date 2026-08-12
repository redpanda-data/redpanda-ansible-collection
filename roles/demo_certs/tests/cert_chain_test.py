"""Run the real demo_certs chain end to end with real openssl/keytool.

The role's control-side artifacts (CA, fetched CSRs, issued certs,
truststore) are relative paths, so each scenario runs ansible-playbook via
subprocess with a controlled cwd.
"""
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest


PLAYBOOK = '/app/tests/demo_certs.yml'
STOREPASS_SENTINEL = 'SENTINEL-STOREPASS-DO-NOT-LOG'


def run_play(workdir, extra_args=(), expect_rc=0):
    inv = os.path.join(workdir, 'inventory')
    with open(inv, 'w') as f:
        f.write('127.0.0.1 ansible_connection=local private_ip=127.0.0.1')
    # ansible resolves relative paths against the playbook directory, so each
    # scenario gets its own copy of the playbook inside its workdir
    playbook = os.path.join(workdir, 'demo_certs.yml')
    if not os.path.exists(playbook):
        shutil.copy(PLAYBOOK, playbook)
        os.symlink('/app/templates', os.path.join(workdir, 'templates'))
    cmd = ['ansible-playbook', '-i', inv, playbook, *extra_args]
    result = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
    if expect_rc is not None:
        assert result.returncode == expect_rc, \
            f"rc={result.returncode}\nstdout tail:\n{result.stdout[-3000:]}\nstderr:\n{result.stderr[-500:]}"
    return result


def recap_changed(stdout):
    m = re.search(r':\s+ok=\d+\s+changed=(\d+)', stdout)
    return int(m.group(1)) if m else None


def mode_of(path):
    return stat.S_IMODE(os.stat(path).st_mode)


class TestDemoCertChain(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.workdir = tempfile.mkdtemp()
        cls.first = run_play(cls.workdir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.workdir, ignore_errors=True)

    def test_chain_produces_verifiable_cert(self):
        ca = os.path.join(self.workdir, 'tls/ca/ca.crt')
        hostname = os.uname().nodename
        node = os.path.join(self.workdir, f'tls/certs/{hostname}/node.crt')
        self.assertTrue(os.path.isfile(ca), "CA cert must exist")
        self.assertTrue(os.path.isfile(node), "issued node cert must exist")
        verify = subprocess.run(['openssl', 'verify', '-CAfile', ca, node],
                                capture_output=True, text=True)
        self.assertEqual(verify.returncode, 0, verify.stderr)

    def test_truststore_created(self):
        hostname = os.uname().nodename
        ts = os.path.join(self.workdir, f'tls/certs/{hostname}/truststore.jks')
        self.assertTrue(os.path.isfile(ts), "truststore must exist")

    def test_private_keys_not_world_readable(self):
        self.assertEqual(mode_of(os.path.join(self.workdir, 'tls/ca/ca.key')), 0o600,
                         "CA private key must be 0600")
        self.assertEqual(mode_of('/etc/redpanda/certs/node.key'), 0o600,
                         "node private key must be 0600")

    def test_rerun_is_idempotent_and_preserves_ca_db(self):
        serial_path = os.path.join(self.workdir, 'tls/ca/serial.txt')
        with open(serial_path) as f:
            serial_before = f.read().strip()
        self.assertNotEqual(serial_before, '01',
                            "issuing a cert must advance the CA serial")

        second = run_play(self.workdir)
        with open(serial_path) as f:
            serial_after = f.read().strip()
        self.assertEqual(serial_after, serial_before,
                         "re-running must not reset the CA serial database")
        self.assertEqual(recap_changed(second.stdout), 0,
                         f"second run must report no changes:\n{second.stdout[-2000:]}")

    def test_storepass_never_in_verbose_output(self):
        workdir = tempfile.mkdtemp()
        try:
            result = run_play(workdir, extra_args=[
                '-v', '-e', f'truststore_password={STOREPASS_SENTINEL}'])
            self.assertNotIn(STOREPASS_SENTINEL, result.stdout,
                             "the truststore password leaked into -v output")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
