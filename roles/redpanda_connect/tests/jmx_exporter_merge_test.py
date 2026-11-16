"""
tasks/generate-jmx-exporter-config.yml must merge jmx_exporter_override into
the rendered JMX exporter config on current ansible-core.

`lookup('template', ...)` returns a string. ansible-core before 2.19 turned a
JSON-looking string into a dict when templating a set_fact value; 2.19 and
later keep it a string, so `combine` fails with "expected dicts but got a
'_AnsibleTaggedStr'" and every Connect deployment stops there.

These tests run the real "Load template contents" and "Merge with
user-provided overrides" tasks with ansible-playbook against localhost and
check the merged config the role would write.
"""
import json
import os
import subprocess
import sys

import pytest
import yaml

ROLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
JMX_TASKS = os.path.join(ROLE_DIR, 'tasks', 'generate-jmx-exporter-config.yml')
MERGE_TASKS = ['Load template contents', 'Merge with user-provided overrides']


def merged_config(tmp_path, extra_vars):
    with open(JMX_TASKS) as f:
        tasks = [t for t in yaml.safe_load(f) if t.get('name') in MERGE_TASKS]
    assert [t['name'] for t in tasks] == MERGE_TASKS
    out = tmp_path / 'jmx-exporter-config.json'
    tasks.append({'ansible.builtin.copy': {
        'content': '{{ jmx_exporter_config | to_nice_json }}', 'dest': str(out)}})

    # lookup('template') resolves relative to the playbook's templates/ dir
    (tmp_path / 'templates').symlink_to(os.path.join(ROLE_DIR, 'templates'))
    playbook = tmp_path / 'play.yml'
    playbook.write_text(yaml.safe_dump([{
        'hosts': 'localhost',
        'gather_facts': False,
        'vars_files': [os.path.join(ROLE_DIR, 'defaults', 'main.yml')],
        'tasks': tasks,
    }]))
    env = dict(os.environ, ANSIBLE_LOCALHOST_WARNING='False', ANSIBLE_NOCOLOR='True')
    proc = subprocess.run(
        ['ansible-playbook', str(playbook), '-e', json.dumps(extra_vars)],
        env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(out.read_text())


def test_defaults_render_to_the_template_config(tmp_path):
    config = merged_config(tmp_path, {})
    assert config['lowercaseOutputName'] is True
    assert config['rules'], 'the template defines JMX rules'


def test_override_is_merged_into_the_template_config(tmp_path):
    config = merged_config(tmp_path, {'jmx_exporter_override': '{"lowercaseOutputName": false}'})
    assert config['lowercaseOutputName'] is False
    assert config['rules'], 'the override keeps the template rules'


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v', '-p', 'no:cacheprovider']))
