import os
import shutil
import tempfile

import pytest
import ansible_runner


# No [connect] group on purpose: the role must tolerate inventories that
# don't define the connect group instead of crashing on
# groups[redpanda_connect_group].
INVENTORY = "node1 ansible_connection=local\n"


def run(extravars):
    work_dir = tempfile.mkdtemp()
    inv = os.path.join(work_dir, 'inventory')
    with open(inv, 'w') as f:
        f.write(INVENTORY)
    try:
        r = ansible_runner.run(
            playbook='/app/tests/groups_default.yml',
            inventory=inv,
            extravars=extravars,
            cmdline='--tags connect_systemd_reload,connect_enable_start',
            quiet=False,
        )
        failures = [
            event['event_data']['res'].get('msg', '')
            for event in r.events
            if event['event'] == 'runner_on_failed'
        ]
        return r.status, failures
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


class TestMissingConnectGroup:

    def test_no_connect_group_does_not_crash(self):
        """An inventory without the connect group must not fail the play.

        Both systemd gate conditions index groups[redpanda_connect_group]
        directly; without a default the conditional itself errors when the
        group is absent.
        """
        status, failures = run({
            'redpanda_connect_group': 'connect',
            # force the reload gate past its first condition so its group
            # lookup is evaluated too
            'systemd_unit_result': {'changed': True},
        })
        assert status == 'successful', \
            f"play must succeed with no connect group in the inventory, failures: {failures}"
        assert not failures, f"no task may fail, got: {failures}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))