import os
import pytest
import ansible_runner
import json
def run_playbook(extra_vars):
    playbook_path = '/app/tests/restart_required.yml'
    inventory_path = '/app/tests/inventory'

    # Ensure the inventory file exists and contains localhost
    with open(inventory_path, 'w') as f:
        f.write('localhost ansible_connection=local')

    # Add mock shell command values to extra_vars
    extra_vars['mock_shell_stdout'] = extra_vars['restart_required_rc']['stdout']
    extra_vars['mock_shell_rc'] = 0 if extra_vars['restart_required_rc']['stdout'] in ['true', 'false'] else 1

    # Run the playbook
    r = ansible_runner.run(
        playbook=playbook_path,
        inventory=inventory_path,
        extravars=extra_vars,
        quiet=False
    )

    # Check if the playbook run was successful
    if r.status != 'successful':
        print(f"Playbook stdout:\n{r.stdout.read()}")
        print(f"Playbook stderr:\n{r.stderr.read()}")
        for event in r.events:
            if event['event'] == 'runner_on_failed':
                print(f"Task failed: {event['event_data']['task']}")
                print(f"Error message: {event['event_data']['res'].get('msg', 'No error message')}")
        assert False, f"Playbook failed: {r.rc}"

    # Parse the output to get the restart_required value
    for event in r.events:
        if event['event'] == 'runner_on_ok' and 'restart_required' in event['event_data']['res'].get('ansible_facts', {}):
            return event['event_data']['res']['ansible_facts']['restart_required']

    raise ValueError("Could not find restart_required in playbook output")

@pytest.mark.parametrize("test_input,expected", [
    (
        {
            "is_initialized": False,
            "nodeconfig_result": {"changed": False},
            "package_result": {"results": []},
            "restart_node": True,
            "restart_required_rc": {"stdout": "false"},
        },
        False
    ),
    (
        {
            "is_initialized": False,
            "nodeconfig_result": {"changed": False},
            "package_result": {"results": []},
            "restart_node": True,
            "restart_required_rc": {"stdout": "true"}
        },
        True
    ),
    (
        {
            "is_initialized": True,
            "nodeconfig_result": {"changed": True},
            "package_result": {"results": []},
            "restart_node": True,
            "restart_required_rc": {"stdout": "false"},
            "mock_template_changed": False
        },
        True
    ),
    (
        {
            "is_initialized": True,
            "nodeconfig_result": {"changed": False},
            "package_result": {"results": ["1 upgraded"]},
            "restart_node": True,
            "restart_required_rc": {"stdout": "false"},
            "mock_template_changed": False
        },
        True
    ),
    (
            {
                "is_initialized": True,
                "nodeconfig_result": {"changed": False},
                "package_result": {"results": []},
                "restart_node": True,
                "restart_required_rc": {"stdout": "true"},
                "mock_template_changed": True
            },
            True
    ),
    (
        {
            "is_initialized": True,
            "nodeconfig_result": {"changed": True},
            "package_result": {"results": ["1 upgraded"]},
            "restart_node": False,
            "restart_required_rc": {"stdout": "true"},
            "mock_template_changed": False
        },
        False
    ),
])
def test_restart_required(test_input, expected):
    restart_required = run_playbook(test_input)
    assert restart_required == expected, f"Expected restart_required to be {expected}, but got {restart_required}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
