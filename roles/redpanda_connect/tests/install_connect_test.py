import hashlib
import os
import shutil
import tempfile

import pytest
import ansible_runner


INVENTORY = """\
[connect]
node1 ansible_connection=local
"""

CONTRACT_MSG = 'Redpanda Connect install contract not satisfied'
RPM_NAME = 'redpanda-connect.x86_64.rpm'


def run(extravars, tags=None):
    work_dir = tempfile.mkdtemp()
    inv = os.path.join(work_dir, 'inventory')
    with open(inv, 'w') as f:
        f.write(INVENTORY)
    try:
        r = ansible_runner.run(
            playbook='/app/tests/install_connect.yml',
            inventory=inv,
            extravars=extravars,
            cmdline=f'--tags {tags}' if tags else None,
            quiet=False,
        )
        failures = [
            str(event['event_data']['res'].get('msg', ''))
            for event in r.events
            if event['event'] == 'runner_on_failed'
        ]
        return r.status, failures
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


class TestInstallContract:

    def test_missing_rpm_and_url_fails_with_named_contract(self):
        """No staged RPM and no download URL must fail with an actionable message.

        The role installs a pre-staged local RPM that nothing downloads;
        without the contract assert the user got an opaque dnf error about a
        missing /tmp path.
        """
        rpm_dir = tempfile.mkdtemp()
        try:
            status, failures = run({
                'redpanda_connect_rpm_dir': rpm_dir,
                'redpanda_connect_rpm': RPM_NAME,
            })
            assert status == 'failed', 'the play must fail when the install contract is unmet'
            assert any(CONTRACT_MSG in msg for msg in failures), \
                f"the failure must name the install contract, got: {failures}"
            assert any('connect_rpm_url' in msg for msg in failures), \
                f"the failure must point at the connect_rpm_url alternative, got: {failures}"
        finally:
            shutil.rmtree(rpm_dir, ignore_errors=True)

    def test_prestaged_rpm_satisfies_the_contract(self):
        rpm_dir = tempfile.mkdtemp()
        try:
            with open(os.path.join(rpm_dir, RPM_NAME), 'wb') as f:
                f.write(b'fake rpm payload')
            status, failures = run({
                'redpanda_connect_rpm_dir': rpm_dir,
                'redpanda_connect_rpm': RPM_NAME,
            }, tags='connect_install_contract')
            assert status == 'successful', f"staged RPM must satisfy the contract, failures: {failures}"
        finally:
            shutil.rmtree(rpm_dir, ignore_errors=True)

    def test_connect_rpm_url_downloads_the_rpm(self):
        rpm_dir = tempfile.mkdtemp()
        src_dir = tempfile.mkdtemp()
        try:
            payload = b'downloadable rpm payload'
            src = os.path.join(src_dir, 'source.rpm')
            with open(src, 'wb') as f:
                f.write(payload)
            checksum = 'sha256:' + hashlib.sha256(payload).hexdigest()

            status, failures = run({
                'redpanda_connect_rpm_dir': rpm_dir,
                'redpanda_connect_rpm': RPM_NAME,
                'connect_rpm_url': f'file://{src}',
                'connect_rpm_checksum': checksum,
            }, tags='connect_install_contract')
            assert status == 'successful', f"download path must satisfy the contract, failures: {failures}"

            dest = os.path.join(rpm_dir, RPM_NAME)
            assert os.path.exists(dest), 'the RPM must be downloaded to the install location'
            with open(dest, 'rb') as f:
                assert f.read() == payload
        finally:
            shutil.rmtree(rpm_dir, ignore_errors=True)
            shutil.rmtree(src_dir, ignore_errors=True)

    def test_wrong_checksum_fails_the_download(self):
        rpm_dir = tempfile.mkdtemp()
        src_dir = tempfile.mkdtemp()
        try:
            src = os.path.join(src_dir, 'source.rpm')
            with open(src, 'wb') as f:
                f.write(b'downloadable rpm payload')

            status, _ = run({
                'redpanda_connect_rpm_dir': rpm_dir,
                'redpanda_connect_rpm': RPM_NAME,
                'connect_rpm_url': f'file://{src}',
                'connect_rpm_checksum': 'sha256:' + '0' * 64,
            }, tags='connect_install_contract')
            assert status == 'failed', 'a checksum mismatch must fail the download'
        finally:
            shutil.rmtree(rpm_dir, ignore_errors=True)
            shutil.rmtree(src_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
