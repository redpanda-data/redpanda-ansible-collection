import os

import ansible_runner
import pytest


# Runs only the device-discovery tasks (and the no-device guard) from
# prepare-data-dir.yml. Device facts are injected via ansible_devices so no
# real block devices are needed; gather_facts is false in the test playbook.
TAGS = 'prep_data_dir_devices'

MOUNT_DIR = '/mnt/vectorized/redpanda'


def run(extravars):
    here = os.path.dirname(os.path.abspath(__file__))

    r = ansible_runner.run(
        playbook=os.path.join(here, 'prep_data_dir_test.yml'),
        inventory=os.path.join(here, 'inventory'),
        extravars=extravars,
        cmdline=f'--tags {TAGS}',
        quiet=False,
    )

    facts = {}
    failures = []
    for event in r.events:
        data = event.get('event_data', {})
        res = data.get('res', {})
        if event['event'] == 'runner_on_ok':
            facts.update(res.get('ansible_facts', {}))
        elif event['event'] == 'runner_on_failed':
            failures.append(res.get('msg', ''))

    return r.status, facts, failures


def assert_guard_fired(status, failures):
    assert status == 'failed', (
        'expected the play to fail when no eligible data device exists; '
        'a green run here means Redpanda would silently deploy on the root disk'
    )
    combined = ' '.join(failures)
    assert 'allow_unmounted_data_dir' in combined, (
        f'guard failure message must mention the escape hatch, got: {combined!r}'
    )


class TestNoEligibleDeviceGuard:

    def test_no_nvme_devices_fails(self):
        status, _, failures = run({
            'ansible_devices': {
                'sda': {'partitions': {'sda1': {}}},
                'loop0': {'partitions': {}},
            },
            'redpanda_mount_dir': MOUNT_DIR,
        })
        assert_guard_fired(status, failures)

    def test_only_partitioned_nvme_fails(self):
        status, _, failures = run({
            'ansible_devices': {
                'nvme0n1': {'partitions': {'nvme0n1p1': {}}},
            },
            'redpanda_mount_dir': MOUNT_DIR,
        })
        assert_guard_fired(status, failures)

    def test_sdb_style_device_names_fail(self):
        # Unpartitioned, but not nvme-named: the resolver only considers nvme*
        # devices, so this must fail loudly instead of skipping every mount
        # task and landing the data dir on the root filesystem.
        status, _, failures = run({
            'ansible_devices': {
                'sdb': {'partitions': {}},
            },
            'redpanda_mount_dir': MOUNT_DIR,
        })
        assert_guard_fired(status, failures)

    def test_escape_hatch_allows_no_device(self):
        for devices in (
            {'sda': {'partitions': {'sda1': {}}}},
            {'nvme0n1': {'partitions': {'nvme0n1p1': {}}}},
            {'sdb': {'partitions': {}}},
        ):
            status, _, failures = run({
                'ansible_devices': devices,
                'redpanda_mount_dir': MOUNT_DIR,
                'allow_unmounted_data_dir': True,
            })
            assert status == 'successful', (
                f'allow_unmounted_data_dir=true must bypass the guard for '
                f'{devices}, failures: {failures}'
            )

    def test_already_mounted_data_dir_passes(self):
        # The volume is already mounted at the data dir's mount point (for
        # example prepared by an image build); no candidate device is required.
        status, _, failures = run({
            'ansible_devices': {
                'nvme0n1': {'partitions': {'nvme0n1p1': {}}},
            },
            'ansible_mounts': [
                {'mount': '/mnt/vectorized', 'device': '/dev/nvme0n1p1'},
                {'mount': '/', 'device': '/dev/sda1'},
            ],
            'redpanda_mount_dir': MOUNT_DIR,
        })
        assert status == 'successful', f'failures: {failures}'

    def test_eligible_device_passes_and_is_selected(self):
        status, facts, failures = run({
            'ansible_devices': {
                'nvme0n1': {'partitions': {}},
                'sda': {'partitions': {'sda1': {}}},
            },
            'redpanda_mount_dir': MOUNT_DIR,
        })
        assert status == 'successful', f'failures: {failures}'
        assert facts.get('nvme_devices_for_raid') == ['/dev/nvme0n1']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
