"""Structural checks on the logging role's handler wiring and idempotency.

The systemd logging override changes where the redpanda process logs, so
it must trigger a redpanda restart; a handler nobody notifies is dead
code, and failed_when: false on a restart handler makes a service that
fails to come back look identical to one that isn't installed.
"""
import unittest

import yaml


def load(path):
    with open(path) as f:
        return yaml.safe_load(f)


def walk(tasks):
    for task in tasks or []:
        if not isinstance(task, dict):
            continue
        yield task
        for section in ('block', 'rescue', 'always'):
            if section in task:
                yield from walk(task[section])


class TestLoggingWiring(unittest.TestCase):

    def setUp(self):
        self.tasks = list(walk(load('/app/tasks/main.yml')))
        self.handlers = load('/app/handlers/main.yml')
        self.notified = set()
        for t in self.tasks:
            n = t.get('notify', [])
            self.notified.update([n] if isinstance(n, str) else n)

    def find(self, name):
        for t in self.tasks:
            if t.get('name') == name:
                return t
        self.fail(f"task {name!r} not found")

    def test_override_notifies_redpanda_restart(self):
        override = self.find('Create systemd logging override')
        notify = override.get('notify', [])
        notify = [notify] if isinstance(notify, str) else notify
        self.assertIn('Restart redpanda', notify,
                      "changing where redpanda logs requires a redpanda restart")

    def test_no_orphan_or_failure_masking_handlers(self):
        for h in self.handlers:
            self.assertIn(h['name'], self.notified,
                          f"handler {h['name']!r} is notified by nothing")
            self.assertNotIn('failed_when', h,
                             f"handler {h['name']!r} must not mask failures")

    def test_max_level_wired_into_override(self):
        override = self.find('Create systemd logging override')
        content = override['ansible.builtin.copy']['content']
        self.assertIn('LogLevelMax={{ redpanda_logging_systemd_max_level }}',
                      content, "the documented max-level knob must take effect")

    def test_forward_to_syslog_removed(self):
        # journald's ForwardToSyslog cannot be set per-service; the variable
        # promised behavior the role cannot deliver
        with open('/app/defaults/main.yml') as f:
            self.assertNotIn('forward_to_syslog', f.read())

    def test_log_file_creation_is_idempotent(self):
        create = self.find('Create initial log file with correct permissions')
        self.assertNotIn('state', str(create.get('ansible.builtin.file', {})),
                         "file state=touch reports changed on every run")
        copy_args = create.get('ansible.builtin.copy')
        self.assertIsNotNone(copy_args, "expected copy with force: false")
        self.assertFalse(copy_args.get('force', True))


if __name__ == '__main__':
    unittest.main()
