import os
import shutil
import stat
import tempfile

import pytest
import ansible_runner


TAGS = ','.join([
    'broker_check_initialized',
    'broker_set_initialized',
    'broker_cluster_initialized',
    'broker_set_cluster_config',
])

# The first play host is deliberately the uninitialized (fresh) node: a
# run_once task gated on the per-host is_initialized would consult the fresh
# node's state and skip cluster-config application for the whole cluster.
INVENTORY_TEMPLATE = """\
[redpanda]
fresh_node ansible_connection=local private_ip=10.0.0.1 redpanda_data_directory={base}/fresh
initialized_node ansible_connection=local private_ip=10.0.0.2 redpanda_data_directory={base}/initialized
"""

MOCK_RPK = """\
#!/bin/bash
if [ "$1 $2 $3" = "cluster config get" ]; then
  echo "null"
  exit 0
fi
echo "Successfully updated configuration."
"""


def run():
    base = tempfile.mkdtemp()
    os.makedirs(os.path.join(base, 'initialized', 'redpanda', 'controller'))
    os.makedirs(os.path.join(base, 'fresh'))

    inv = '/app/tests/inventory'
    with open(inv, 'w') as f:
        f.write(INVENTORY_TEMPLATE.format(base=base))

    mock_dir = tempfile.mkdtemp()
    mock_path = os.path.join(mock_dir, 'rpk')
    with open(mock_path, 'w') as f:
        f.write(MOCK_RPK)
    os.chmod(mock_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    try:
        r = ansible_runner.run(
            playbook='/app/tests/cluster_config_gate.yml',
            inventory=inv,
            cmdline=f'--tags {TAGS}',
            envvars={'PATH': f"{mock_dir}:{os.environ.get('PATH', '')}"},
            quiet=False
        )
        assert r.status == 'successful', f"Playbook failed: {r.rc}"

        applied = []
        for event in r.events:
            if event['event'] == 'runner_on_ok':
                if event['event_data'].get('task') == 'Set cluster config (for running cluster updates)':
                    applied.append(event['event_data'].get('host'))
        return applied
    finally:
        shutil.rmtree(base)
        shutil.rmtree(mock_dir)


class TestClusterConfigGate:

    def test_cluster_config_applied_when_any_node_initialized(self):
        # A fresh node joining an existing cluster sorts first in the play:
        # cluster config must still be applied for the cluster.
        applied = run()
        assert applied, (
            "Set cluster config must run when the cluster is initialized, "
            "even if the run_once host is a freshly added node"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))