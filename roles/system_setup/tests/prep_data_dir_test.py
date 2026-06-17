import pytest
import ansible_runner
import os
import stat
import tempfile
import shutil


MOCK_UUID = "11111111-2222-3333-4444-555555555555"

# blkid is mocked on PATH so the test never needs a real block device. It
# ignores its arguments and returns a fixed UUID, which is what the role pipes
# into the fstab src.
MOCK_BLKID = """\
#!/bin/bash
echo "{uuid}"
""".format(uuid=MOCK_UUID)

TAGS = 'prep_data_dir_resolve'


def run(extravars):
    here = os.path.dirname(os.path.abspath(__file__))
    inv = os.path.join(here, 'inventory')

    # Write mock blkid to a temp dir placed at the front of PATH so it shadows
    # any real blkid without polluting PATH for other tests.
    mock_dir = tempfile.mkdtemp()
    mock_path = os.path.join(mock_dir, 'blkid')
    with open(mock_path, 'w') as f:
        f.write(MOCK_BLKID)
    os.chmod(mock_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    try:
        r = ansible_runner.run(
            playbook=os.path.join(here, 'prep_data_dir_test.yml'),
            inventory=inv,
            extravars=extravars,
            cmdline=f'--tags {TAGS}',
            envvars={'PATH': f"{mock_dir}:{os.environ.get('PATH', '')}"},
            quiet=False
        )

        # Accumulate every fact set by the set_fact tasks that ran.
        facts = {}
        for event in r.events:
            if event['event'] == 'runner_on_ok':
                res = event.get('event_data', {}).get('res', {})
                facts.update(res.get('ansible_facts', {}))

        return r.status, facts
    finally:
        shutil.rmtree(mock_dir)


class TestPrepDataDir:

    def test_single_device_mounts_by_uuid(self):
        status, facts = run({
            'nvme_devices_for_raid': ['/dev/nvme0n1'],
            'ephemeral_disk': False,
            'data_dir_device_timeout': '15s',
        })
        assert status == 'successful'
        src = facts.get('data_dir_mount_src')
        assert src == f"UUID={MOCK_UUID}", f"expected UUID-based src, got {src}"
        # Regression guard: the fstab src must never be a raw device path again.
        assert not src.startswith('/dev/'), f"src must not be a raw device path, got {src}"

    def test_persistent_opts_have_no_nofail(self):
        status, facts = run({
            'nvme_devices_for_raid': ['/dev/nvme0n1'],
            'ephemeral_disk': False,
            'data_dir_device_timeout': '15s',
        })
        assert status == 'successful'
        assert facts.get('data_dir_mount_opts') == 'defaults,x-systemd.device-timeout=15s'

    def test_raid_mounts_by_uuid(self):
        status, facts = run({
            'nvme_devices_for_raid': ['/dev/nvme0n1', '/dev/nvme1n1'],
            'ephemeral_disk': False,
            'data_dir_device_timeout': '15s',
        })
        assert status == 'successful'
        src = facts.get('data_dir_mount_src')
        assert src == f"UUID={MOCK_UUID}", f"expected UUID-based src for raid, got {src}"
        assert not src.startswith('/dev/'), f"src must not be a raw device path, got {src}"

    def test_ephemeral_opts_add_nofail(self):
        status, facts = run({
            'nvme_devices_for_raid': ['/dev/nvme0n1'],
            'ephemeral_disk': True,
            'data_dir_device_timeout': '15s',
        })
        assert status == 'successful'
        assert facts.get('data_dir_mount_opts') == 'defaults,nofail,x-systemd.device-timeout=15s'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
