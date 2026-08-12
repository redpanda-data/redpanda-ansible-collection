import pytest
import ansible_runner


AIRGAP_FILES = [
    '/app/tasks/install-rp-deb-airgap.yml',
    '/app/tasks/install-rp-rpm-airgap.yml',
]


def run_playbook(airgap_tasks_file, redpanda_version):
    inventory_path = '/app/tests/inventory'
    with open(inventory_path, 'w') as f:
        f.write('localhost ansible_connection=local')

    r = ansible_runner.run(
        playbook='/app/tests/airgap_gate.yml',
        inventory=inventory_path,
        extravars={
            'airgap_tasks_file': airgap_tasks_file,
            'redpanda_version': redpanda_version,
        },
        cmdline='--tags broker_airgap_post_split',
        quiet=False
    )
    assert r.status == 'successful', f"Playbook failed: {r.rc}"

    for event in r.events:
        if event['event'] == 'runner_on_ok':
            facts = event['event_data']['res'].get('ansible_facts', {})
            if 'is_post_split' in facts:
                return facts['is_post_split']

    raise ValueError("Could not find is_post_split in playbook output")


@pytest.mark.parametrize("airgap_tasks_file", AIRGAP_FILES,
                         ids=['deb', 'rpm'])
@pytest.mark.parametrize("redpanda_version,expected", [
    ('latest', True),
    ('24.1.9-1', False),
    ('24.2.1-1', True),
    ('25.1.1-1', True),
    # double-digit minors sort before '24.2' as strings; the gate must
    # compare versions, not strings
    ('24.10.1-1', True),
    ('24.11.2-1', True),
])
def test_airgap_package_split_gate(airgap_tasks_file, redpanda_version, expected):
    is_post_split = run_playbook(airgap_tasks_file, redpanda_version)
    assert bool(is_post_split) == expected, \
        f"{redpanda_version}: expected is_post_split={expected}, got {is_post_split}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))