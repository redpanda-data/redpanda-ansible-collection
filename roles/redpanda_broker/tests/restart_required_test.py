import os
import stat
import tempfile
import shutil

import pytest
import ansible_runner


TAGS = 'broker_check_restart,broker_check_restart_noauth,broker_restart_required'

# Mimics `rpk cluster config status` closely enough for the role's pipeline:
# grep '^<node_id> ' | awk '{ print $3 }' | grep -E 'true|false'
RPK_STATUS_TEMPLATE = """\
#!/bin/bash
cat <<'OUTPUT'
NODE  CONFIG-VERSION  NEEDS-RESTART  INVALID  UNKNOWN
0 2 {needs_restart} [] []
OUTPUT
"""


def run_playbook(extra_vars, needs_restart):
    playbook_path = '/app/tests/restart_required.yml'
    inventory_path = '/app/tests/inventory'

    with open(inventory_path, 'w') as f:
        f.write('localhost ansible_connection=local')

    mock_dir = tempfile.mkdtemp()
    mock_path = os.path.join(mock_dir, 'rpk')
    with open(mock_path, 'w') as f:
        f.write(RPK_STATUS_TEMPLATE.format(needs_restart=needs_restart))
    os.chmod(mock_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    try:
        r = ansible_runner.run(
            playbook=playbook_path,
            inventory=inventory_path,
            extravars=extra_vars,
            cmdline=f'--tags {TAGS}',
            envvars={'PATH': f"{mock_dir}:{os.environ.get('PATH', '')}"},
            quiet=False
        )

        if r.status != 'successful':
            for event in r.events:
                if event['event'] == 'runner_on_failed':
                    print(f"Task failed: {event['event_data']['task']}")
                    print(f"Error message: {event['event_data']['res'].get('msg', 'No error message')}")
            assert False, f"Playbook failed: {r.rc}"

        for event in r.events:
            if event['event'] == 'runner_on_ok':
                facts = event['event_data']['res'].get('ansible_facts', {})
                if 'restart_required' in facts:
                    return facts['restart_required']

        raise ValueError("Could not find restart_required in playbook output")
    finally:
        shutil.rmtree(mock_dir)


@pytest.mark.parametrize("test_input,needs_restart,expected", [
    # rpk reports no restart needed, nothing else changed -> no restart
    (
        {
            "kafka_enable_authorization": False,
            "is_initialized": False,
            "nodeconfig_result": {"changed": False},
            "package_result": {"changed": False},
            "restart_node": True,
        },
        "false",
        False
    ),
    # rpk reports restart needed (no auth) -> restart
    (
        {
            "kafka_enable_authorization": False,
            "is_initialized": False,
            "nodeconfig_result": {"changed": False},
            "package_result": {"changed": False},
            "restart_node": True,
        },
        "true",
        True
    ),
    # node config changed on an initialized cluster -> restart
    (
        {
            "kafka_enable_authorization": False,
            "is_initialized": True,
            "nodeconfig_result": {"changed": True},
            "package_result": {"changed": False},
            "restart_node": True,
        },
        "false",
        True
    ),
    # rpk reports restart needed with SASL auth enabled -> restart.
    # Exercises the auth variant of the restart check; the skipped no-auth
    # twin must not clobber its registered result.
    (
        {
            "kafka_enable_authorization": True,
            "is_initialized": False,
            "nodeconfig_result": {"changed": False},
            "package_result": {"changed": False},
            "restart_node": True,
        },
        "true",
        True
    ),
    # SASL auth enabled, no restart needed -> no restart
    (
        {
            "kafka_enable_authorization": True,
            "is_initialized": False,
            "nodeconfig_result": {"changed": False},
            "package_result": {"changed": False},
            "restart_node": True,
        },
        "false",
        False
    ),
    # user opted out of managed restarts -> never restart
    (
        {
            "kafka_enable_authorization": False,
            "is_initialized": True,
            "nodeconfig_result": {"changed": True},
            "package_result": {"changed": True},
            "restart_node": False,
        },
        "true",
        False
    ),
])
def test_restart_required(test_input, needs_restart, expected):
    restart_required = run_playbook(test_input, needs_restart)
    assert restart_required == expected, \
        f"Expected restart_required to be {expected}, but got {restart_required}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
