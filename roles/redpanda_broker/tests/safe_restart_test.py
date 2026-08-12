import os
import shutil
import stat
import tempfile

import pytest
import ansible_runner


SKIP_TAGS = 'safe_restart_write_config,safe_restart_restart,safe_restart_wait_port'

INVENTORY = """\
[redpanda]
node1 ansible_connection=local private_ip=10.0.0.1
node2 ansible_connection=local private_ip=10.0.0.2
"""

MOCK_RPK_HEALTHY = """\
#!/bin/bash
if [ "$1 $2" = "cluster health" ]; then
  cat <<'OUTPUT'
CLUSTER HEALTH OVERVIEW
=======================
Healthy:                          true
Controller ID:                    0
OUTPUT
  exit 0
fi
exit 0
"""

MOCK_RPK_NEVER_HEALTHY = """\
#!/bin/bash
if [ "$1 $2" = "cluster health" ]; then
  cat <<'OUTPUT'
CLUSTER HEALTH OVERVIEW
=======================
Healthy:                          false
Controller ID:                    0
OUTPUT
  exit 0
fi
exit 0
"""


def run(mock_rpk, extravars=None):
    inv = '/app/tests/inventory'
    with open(inv, 'w') as f:
        f.write(INVENTORY)

    mock_dir = tempfile.mkdtemp()
    mock_path = os.path.join(mock_dir, 'rpk')
    with open(mock_path, 'w') as f:
        f.write(mock_rpk)
    os.chmod(mock_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    try:
        r = ansible_runner.run(
            playbook='/app/tests/safe_restart.yml',
            inventory=inv,
            extravars=extravars or {},
            cmdline=f'--skip-tags {SKIP_TAGS}',
            envvars={'PATH': f"{mock_dir}:{os.environ.get('PATH', '')}"},
            quiet=False
        )
        task_sequence = []
        for event in r.events:
            if event['event'] == 'runner_on_ok':
                task_sequence.append(event['event_data'].get('task'))
        return r.status, task_sequence
    finally:
        shutil.rmtree(mock_dir)


class TestSafeRestartReadinessGate:

    def test_health_gate_runs_between_restart_and_mm_disable(self):
        status, tasks = run(MOCK_RPK_HEALTHY)
        assert status == 'successful'
        assert 'Wait for cluster health after restart' in tasks, \
            "restart must be followed by a cluster-health readiness gate"
        health = tasks.index('Wait for cluster health after restart')
        disable = tasks.index('Disable Maintenance Mode')
        assert health < disable, \
            "the node must be back healthy before leaving maintenance mode"

    def test_unhealthy_cluster_fails_instead_of_proceeding(self):
        status, tasks = run(
            MOCK_RPK_NEVER_HEALTHY,
            extravars={'restart_health_retries': 2, 'restart_health_delay': 0},
        )
        assert status == 'failed', \
            "a node that never reports healthy must fail the play"
        assert 'Disable Maintenance Mode' not in tasks, \
            "maintenance mode must not be lifted on an unhealthy cluster"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))