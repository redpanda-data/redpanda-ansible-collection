import pytest
import ansible_runner
import os
import stat
import tempfile
import shutil


INVENTORY = """\
[redpanda]
node0 ansible_connection=local private_ip=10.0.0.1
node1 ansible_connection=local private_ip=10.0.0.10
node2 ansible_connection=local private_ip=10.0.0.100
"""

MOCK_RPK = """\
#!/bin/bash
cat <<'OUTPUT'
CLUSTER
=======
redpanda.test-cluster

BROKERS
=======
ID    HOST         PORT
0     10.0.0.1     9092
1*    10.0.0.10    9092
2     10.0.0.100   9092
OUTPUT
"""

TAGS = 'broker_node_id,broker_set_node_id'


def run():
    inv = '/app/tests/inventory'
    with open(inv, 'w') as f:
        f.write(INVENTORY)

    # Write mock rpk to a temp directory so it doesn't pollute PATH
    # for other tests (rpk_config_idempotency_test skips when rpk is absent)
    mock_dir = tempfile.mkdtemp()
    mock_path = os.path.join(mock_dir, 'rpk')
    with open(mock_path, 'w') as f:
        f.write(MOCK_RPK)
    os.chmod(mock_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    try:
        r = ansible_runner.run(
            playbook='/app/tests/node_id_test.yml',
            inventory=inv,
            cmdline=f'--tags {TAGS}',
            envvars={'PATH': f"{mock_dir}:{os.environ.get('PATH', '')}"},
            quiet=False
        )

        node_ids = {}
        for event in r.events:
            if event['event'] == 'runner_on_ok':
                event_data = event.get('event_data', {})
                res = event_data.get('res', {})
                task = event_data.get('task', '')
                host = event_data.get('host', '')
                if 'Set node id' in task:
                    facts = res.get('ansible_facts', {})
                    if 'node_id' in facts:
                        node_ids[host] = str(facts['node_id'])

        return r.status, node_ids
    finally:
        shutil.rmtree(mock_dir)


class TestNodeIdExtraction:

    def test_node_id_exact_match(self):
        status, node_ids = run()
        assert status == 'successful'
        assert node_ids['node0'] == '0', f"10.0.0.1 should map to node 0, got {node_ids.get('node0')}"
        assert node_ids['node1'] == '1', f"10.0.0.10 should map to node 1, got {node_ids.get('node1')}"
        assert node_ids['node2'] == '2', f"10.0.0.100 should map to node 2, got {node_ids.get('node2')}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
