"""
The rolling restart in tasks/safe-restart.yml must pass the SASL superuser
credentials to rpk when kafka_enable_authorization is on.

With admin_api_require_auth enabled, rpk can't authenticate to the Admin API
from the credentials the role writes into redpanda.yaml (a restarted broker
answers "Bad Request, Malformed Authorization header"), so `rpk cluster
maintenance disable` fails right after the restart and leaves the node in
maintenance mode. Every other rpk call in the role passes RPK_USER/RPK_PASS in
its environment; the maintenance-mode tasks must too, and must leave them unset
when SASL is off, because rpk rejects empty credential variables.

These tests run the real maintenance-mode tasks from safe-restart.yml with
ansible-playbook against two local hosts. A stand-in `rpk` on PATH records each
call and the credentials it received.
"""
import json
import os
import stat
import subprocess
import sys

import pytest
import yaml

ROLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SAFE_RESTART = os.path.join(ROLE_DIR, 'tasks', 'safe-restart.yml')

FAKE_RPK = """#!/bin/sh
printf 'args=%s RPK_USER=%s RPK_PASS=%s\\n' "$*" "${RPK_USER-<unset>}" "${RPK_PASS-<unset>}" >> "$FAKE_RPK_LOG"
"""


def maintenance_tasks():
    with open(SAFE_RESTART) as f:
        tasks = yaml.safe_load(f)
    found = [t for t in tasks if 'Maintenance Mode' in t.get('name', '')]
    assert [t['name'] for t in found] == ['Enable Maintenance Mode', 'Disable Maintenance Mode']
    return found


def run_maintenance(tmp_path, *, kafka_enable_authorization):
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    rpk = bindir / 'rpk'
    rpk.write_text(FAKE_RPK)
    rpk.chmod(rpk.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / 'rpk.log'
    log.write_text('')

    tasks_file = tmp_path / 'maintenance.yml'
    tasks_file.write_text(yaml.safe_dump(maintenance_tasks()))
    inventory = tmp_path / 'hosts.ini'
    inventory.write_text('[redpanda]\nnode1 ansible_connection=local\nnode2 ansible_connection=local\n')
    playbook = tmp_path / 'play.yml'
    playbook.write_text(yaml.safe_dump([{
        'hosts': 'redpanda',
        'gather_facts': False,
        'tasks': [{'ansible.builtin.include_tasks': str(tasks_file)}],
    }]))
    extra_vars = {
        'restart_required': True,
        'cluster_host': 'node1',
        'node_id': 0,
        'kafka_enable_authorization': kafka_enable_authorization,
        'sasl_superuser_username': 'admin',
        'sasl_superuser_password': 'not-the-real-password',
        'redpanda_rpk_opts': '--config /etc/redpanda/redpanda.yaml',
        'redpanda_broker_no_log': False,
    }
    env = dict(os.environ,
               PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}",
               FAKE_RPK_LOG=str(log),
               ANSIBLE_NOCOLOR='True')
    proc = subprocess.run(
        ['ansible-playbook', '-i', str(inventory), str(playbook), '-e', json.dumps(extra_vars)],
        env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return log.read_text().splitlines()


def test_sasl_cluster_maintenance_mode_gets_the_superuser_credentials(tmp_path):
    calls = run_maintenance(tmp_path, kafka_enable_authorization=True)
    assert calls == [
        'args=cluster maintenance enable 0 --wait --config /etc/redpanda/redpanda.yaml '
        'RPK_USER=admin RPK_PASS=not-the-real-password',
        'args=cluster maintenance disable 0 --config /etc/redpanda/redpanda.yaml '
        'RPK_USER=admin RPK_PASS=not-the-real-password',
    ]


def test_cluster_without_sasl_leaves_the_credentials_unset(tmp_path):
    calls = run_maintenance(tmp_path, kafka_enable_authorization=False)
    assert calls == [
        'args=cluster maintenance enable 0 --wait --config /etc/redpanda/redpanda.yaml '
        'RPK_USER=<unset> RPK_PASS=<unset>',
        'args=cluster maintenance disable 0 --config /etc/redpanda/redpanda.yaml '
        'RPK_USER=<unset> RPK_PASS=<unset>',
    ]


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v', '-p', 'no:cacheprovider']))
