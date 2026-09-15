"""Structural tests over service start/restart semantics and config handling.

start-console.yml used state: restarted with no condition and no become:
every play bounced the console even when nothing changed, and on top of
that the 'Reload systemd and restart console' handler fired for real
changes - a double restart. The start task must only ensure the service is
running (state: started, with become like every other privileged task) and
leave restarts to the notify handler.

For the handler to cover config changes, the task that writes the console
config must notify it. And since the rendered config can carry secrets
(SASL credentials or login providers merged in via the rpconsole override
variable), the file must not be world-readable - it is owned by the
console user, which is the only reader.
"""
import os

import pytest
import yaml

TASKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tasks')


def load_tasks(name):
    with open(os.path.join(TASKS_DIR, name)) as f:
        return yaml.safe_load(f)


def find_task(tasks, predicate):
    for task in tasks:
        if predicate(task):
            return task
    return None


def get_module_args(task, *modules):
    for module in modules:
        if module in task:
            return task[module]
    return None


class TestStartConsole:

    def systemd_task(self):
        tasks = load_tasks('start-console.yml')
        task = find_task(
            tasks,
            lambda t: get_module_args(t, 'ansible.builtin.systemd', 'systemd',
                                      'ansible.builtin.systemd_service') is not None,
        )
        assert task is not None, "start-console.yml has no systemd task"
        return task

    def test_start_task_uses_started_not_restarted(self):
        args = get_module_args(self.systemd_task(), 'ansible.builtin.systemd',
                               'systemd', 'ansible.builtin.systemd_service')
        assert args.get('state') == 'started', (
            "start-console.yml must use state: started; an unconditional "
            "state: restarted bounces the service on every run and doubles up "
            "with the restart handler"
        )

    def test_start_task_escalates(self):
        task = self.systemd_task()
        assert task.get('become') is True, (
            "the start task manages a system service and needs become: true"
        )


class TestConfigWrite:

    def config_task(self):
        tasks = load_tasks('configure-console.yml')
        task = find_task(
            tasks,
            lambda t: (get_module_args(t, 'ansible.builtin.template', 'template')
                       or {}).get('dest') == '/etc/redpanda/redpanda-console-config.yaml',
        )
        assert task is not None, "config-writing template task not found"
        return task

    def test_config_change_notifies_restart_handler(self):
        task = self.config_task()
        notify = task.get('notify')
        notify = [notify] if isinstance(notify, str) else (notify or [])
        assert 'Reload systemd and restart console' in notify, (
            "the config write must notify the restart handler; with the start "
            "task fixed to state: started, nothing else applies config changes"
        )

    def test_config_file_not_world_readable(self):
        args = get_module_args(self.config_task(), 'ansible.builtin.template', 'template')
        mode = str(args.get('mode', ''))
        assert mode and int(mode[-1], 8) == 0, (
            f"console config mode {mode!r} is world-readable but the rendered "
            f"config can carry SASL/login secrets via rpconsole overrides"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
