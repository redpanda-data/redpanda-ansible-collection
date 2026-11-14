"""
A Redpanda package upgrade on a running cluster must leave the restart to the
role's rolling restart (tasks/safe-restart.yml), one broker at a time.

Three things used to restart every broker at once instead:

* "Stop redpanda after installation (for SASL bootstrap)" ran whenever SASL was
  on and the package changed, so an upgrade of a SASL cluster stopped every
  broker together. It exists for a fresh node's SASL bootstrap only.
* The deb's postinst runs `deb-systemd-invoke try-restart redpanda.service` on
  upgrade, and Ansible upgrades every broker in parallel.
* restart_required only recognised dnf's per-package strings, so an apt (or
  looped dnf) upgrade never asked for the rolling restart.

These tests run the real install-rp-deb.yml / install-rp-rpm.yml tasks and the
real "Establish whether restart required" task with ansible-playbook against
localhost. The package-manager and systemd tasks are replaced by stand-ins that
record what they would have done. Needs root (it manages /usr/sbin/policy-rc.d),
so it runs in the role's test container.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest
import yaml

ROLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TASKS_DIR = os.path.join(ROLE_DIR, 'tasks')
POLICY_RC = '/usr/sbin/policy-rc.d'
PACKAGE_MODULES = ('apt', 'ansible.builtin.apt', 'dnf', 'ansible.builtin.dnf')
SYSTEMD_MODULES = ('systemd', 'ansible.builtin.systemd', 'ansible.builtin.systemd_service')


def stand_in(task, tmp_path):
    task = dict(task)
    for section in ('block', 'rescue', 'always'):
        if section in task:
            task[section] = [stand_in(t, tmp_path) for t in task[section]]
    for mod in PACKAGE_MODULES:
        if mod in task:
            del task[mod]
            # What the deb's postinst would get from policy-rc.d for its try-restart
            # (101 = denied), or "none" when no policy is installed.
            task['ansible.builtin.shell'] = (
                f'if [ -x {POLICY_RC} ]; then {POLICY_RC} redpanda.service restart; echo $?; '
                f'else echo none; fi >> {tmp_path}/install.log')
            task['changed_when'] = 'fake_package_changed | bool'
    for mod in SYSTEMD_MODULES:
        if mod in task:
            args = task.pop(mod)
            task['ansible.builtin.lineinfile'] = {
                'path': str(tmp_path / 'systemd.log'), 'create': True,
                'line': f"{args.get('name')} {args.get('state')}"}
    for key in ('ansible.builtin.include_tasks', 'include_tasks'):
        if key in task and not os.path.isabs(task[key]):
            task[key] = os.path.join(TASKS_DIR, task[key])
    for key in ('ansible.builtin.file', 'file'):
        if key in task and isinstance(task[key], dict):
            task[key] = {k: v for k, v in task[key].items() if k not in ('owner', 'group')}
    return task


def converge(tmp_path, install_file, *, sasl, cluster_data, package_changed=True):
    data_dir = tmp_path / 'data'
    if cluster_data:
        (data_dir / 'redpanda' / 'controller').mkdir(parents=True)

    with open(os.path.join(TASKS_DIR, install_file)) as f:
        tasks = [stand_in(t, tmp_path) for t in yaml.safe_load(f)]
    with open(os.path.join(TASKS_DIR, 'start-redpanda.yml')) as f:
        tasks += [t for t in yaml.safe_load(f) if t.get('name') == 'Establish whether restart required']
    assert tasks[-1]['name'] == 'Establish whether restart required'
    tasks.append({'ansible.builtin.copy': {
        'dest': str(tmp_path / 'result.json'),
        'content': '{{ {"restart_required": restart_required | bool} | to_json }}'}})

    playbook = tmp_path / 'play.yml'
    playbook.write_text(yaml.safe_dump([{
        'hosts': 'localhost', 'gather_facts': False, 'tasks': tasks}]))
    extra_vars = {
        'ansible_os_family': 'Debian' if 'deb' in install_file else 'RedHat',
        'ansible_system_vendor': 'Amazon EC2',
        'redpanda_version': 'latest',
        'redpanda_install_status': 'latest',
        'redpanda_data_directory': str(data_dir),
        'kafka_enable_authorization': sasl,
        'enable_fips': False,
        'fake_package_changed': package_changed,
        # what start-redpanda.yml has established by the time it decides on a restart
        'is_initialized': cluster_data,
        'restart_required_rc': {'stdout': ''},
        'nodeconfig_result': {'changed': False},
    }
    env = dict(os.environ, ANSIBLE_LOCALHOST_WARNING='False', ANSIBLE_NOCOLOR='True')
    proc = subprocess.run(['ansible-playbook', str(playbook), '-e', json.dumps(extra_vars)],
                          env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    def lines(name):
        p = tmp_path / name
        return p.read_text().split() if p.exists() else []
    return {
        'restart_required': json.loads((tmp_path / 'result.json').read_text())['restart_required'],
        'stopped': 'redpanda stopped' in (tmp_path / 'systemd.log').read_text()
        if (tmp_path / 'systemd.log').exists() else False,
        'install_policy': lines('install.log'),
        'cluster_data_kept': (data_dir / 'redpanda' / 'controller').exists(),
    }


@pytest.fixture(autouse=True)
def no_policy_rc(tmp_path_factory):
    # Debian container images ship their own policy-rc.d; set it aside so each test
    # starts from a host without one, and put it back afterwards.
    saved = None
    if os.path.exists(POLICY_RC):
        saved = tmp_path_factory.mktemp('policy') / 'policy-rc.d'
        shutil.move(POLICY_RC, saved)
    yield
    if os.path.exists(POLICY_RC):
        os.remove(POLICY_RC)
    if saved:
        shutil.move(saved, POLICY_RC)


@pytest.mark.parametrize('install_file', ['install-rp-deb.yml', 'install-rp-rpm.yml'])
@pytest.mark.parametrize('sasl', [True, False])
def test_upgrade_of_a_running_broker_waits_for_the_rolling_restart(tmp_path, install_file, sasl):
    result = converge(tmp_path, install_file, sasl=sasl, cluster_data=True)
    assert not result['stopped'], 'the upgrade stopped redpanda outside the rolling restart'
    assert result['cluster_data_kept']
    assert result['restart_required'], 'the upgraded broker was not queued for the rolling restart'


def test_deb_upgrade_blocks_the_package_restart_and_cleans_up(tmp_path):
    result = converge(tmp_path, 'install-rp-deb.yml', sasl=True, cluster_data=True)
    assert result['install_policy'] and set(result['install_policy']) == {'101'}, result
    assert not os.path.exists(POLICY_RC), 'the restart block was left installed'


def test_existing_policy_rc_is_left_alone(tmp_path):
    with open(POLICY_RC, 'w') as f:
        f.write('#!/bin/sh\nexit 0\n')
    os.chmod(POLICY_RC, 0o755)
    converge(tmp_path, 'install-rp-deb.yml', sasl=False, cluster_data=True)
    with open(POLICY_RC) as f:
        assert f.read() == '#!/bin/sh\nexit 0\n'


@pytest.mark.parametrize('install_file', ['install-rp-deb.yml', 'install-rp-rpm.yml'])
def test_fresh_sasl_node_is_still_stopped_for_bootstrap(tmp_path, install_file):
    result = converge(tmp_path, install_file, sasl=True, cluster_data=False)
    assert result['stopped']
    assert not result['restart_required']


@pytest.mark.parametrize('install_file', ['install-rp-deb.yml', 'install-rp-rpm.yml'])
def test_reconverge_without_a_package_change_does_not_restart(tmp_path, install_file):
    result = converge(tmp_path, install_file, sasl=True, cluster_data=True, package_changed=False)
    assert not result['stopped']
    assert not result['restart_required']


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v', '-p', 'no:cacheprovider']))
