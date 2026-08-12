import os

import ansible_runner
import pytest


# Runs only the mount tasks (and the mdadm array definition) from
# prepare-data-dir.yml, in check mode so nothing is actually mounted. The
# candidate device list and resolved fstab src are injected via extra vars;
# assertions are made against the real module args recorded in runner events.
TAGS = 'prep_data_dir_mount'

MOCK_SRC = 'UUID=11111111-2222-3333-4444-555555555555'


def run(extravars):
    here = os.path.dirname(os.path.abspath(__file__))

    r = ansible_runner.run(
        playbook=os.path.join(here, 'prep_data_dir_test.yml'),
        inventory=os.path.join(here, 'inventory'),
        extravars=extravars,
        cmdline=f'--tags {TAGS} --check',
        verbosity=1,
        quiet=False,
    )

    facts = {}
    mount_args = []
    for event in r.events:
        data = event.get('event_data', {})
        res = data.get('res', {})
        if event['event'] != 'runner_on_ok':
            continue
        facts.update(res.get('ansible_facts', {}))
        if data.get('task_action') in ('ansible.posix.mount', 'mount'):
            # The mount module echoes its resolved arguments (name/src/opts/...)
            # in the task result, so assert on those directly.
            mount_args.append(res)

    return r.status, facts, mount_args


BASE_VARS = {
    'data_dir_mount_src': MOCK_SRC,
    'data_dir_mount_opts': 'defaults,x-systemd.device-timeout=15s',
    'ephemeral_disk': False,
    'redpanda_mount_dir': '/data/redpanda',
}


class TestMountPathFollowsVariable:

    def test_single_device_mount_path_derives_from_mount_dir(self):
        status, _, mount_args = run({
            **BASE_VARS,
            'nvme_devices_for_raid': ['/dev/nvme0n1'],
        })
        assert status == 'successful'
        assert len(mount_args) == 1, f'expected one mount invocation, got {mount_args}'
        assert mount_args[0].get('name') == '/data', (
            'mount path must derive from redpanda_mount_dir '
            f'(got {mount_args[0].get("name")!r}); a hardcoded mount point '
            'strands overridden data dirs on the root filesystem'
        )
        assert mount_args[0].get('src') == MOCK_SRC

    def test_raid_mount_path_derives_from_mount_dir(self):
        status, facts, mount_args = run({
            **BASE_VARS,
            'nvme_devices_for_raid': ['/dev/nvme0n1', '/dev/nvme1n1'],
        })
        assert status == 'successful'
        assert len(mount_args) == 1, f'expected one mount invocation, got {mount_args}'
        assert mount_args[0].get('name') == '/data', (
            f'raid mount path must derive from redpanda_mount_dir, '
            f'got {mount_args[0].get("name")!r}'
        )
        # The mdadm array definition must target the same mount point.
        arrays = facts.get('mdadm_arrays')
        assert arrays and arrays[0].get('mountpoint') == '/data', (
            f'mdadm mountpoint must derive from redpanda_mount_dir, got {arrays}'
        )

    def test_default_mount_dir_keeps_default_mount_point(self):
        # Without an override the historical mount point must be preserved.
        base = {k: v for k, v in BASE_VARS.items() if k != 'redpanda_mount_dir'}
        status, _, mount_args = run({
            **base,
            'nvme_devices_for_raid': ['/dev/nvme0n1'],
        })
        assert status == 'successful'
        assert len(mount_args) == 1, f'expected one mount invocation, got {mount_args}'
        assert mount_args[0].get('name') == '/mnt/vectorized'


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))