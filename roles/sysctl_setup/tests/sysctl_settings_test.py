"""Pin the exact sysctl settings this role manages: these values change
host panic behavior and inotify limits, so any drift must be a deliberate,
visible change."""
import unittest

import yaml


class TestSysctlSettings(unittest.TestCase):

    def setUp(self):
        with open('/app/tasks/main.yml') as f:
            self.tasks = yaml.safe_load(f)
        with open('/app/defaults/main.yml') as f:
            self.defaults = yaml.safe_load(f)

    def managed(self):
        settings = {}
        for task in self.tasks:
            args = task.get('ansible.posix.sysctl')
            self.assertIsNotNone(args, f"unexpected module in {task.get('name')}")
            settings[args['name']] = args
        return settings

    def test_managed_keys_and_defaults(self):
        settings = self.managed()
        self.assertEqual(
            set(settings), {'fs.inotify.max_user_instances', 'kernel.panic_on_oops'})
        self.assertEqual(self.defaults['max_user_instances'], 8192)
        self.assertEqual(self.defaults['kernel_panic_on_oops'], 1)

    def test_settings_are_persisted_and_reloaded(self):
        for name, args in self.managed().items():
            self.assertTrue(args.get('sysctl_set'), name)
            self.assertTrue(args.get('reload'), name)
            self.assertEqual(args.get('state'), 'present', name)

    def test_tasks_escalate(self):
        for task in self.tasks:
            self.assertTrue(task.get('become'), task.get('name'))


if __name__ == '__main__':
    unittest.main()
