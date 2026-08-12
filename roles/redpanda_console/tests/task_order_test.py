"""Structural tests over tasks/main.yml ordering.

The console config template choice (use_pre_v3_template) is finalized by the
install task files when redpanda_version == 'latest' (they inspect the version
that was actually installed). Configuration must therefore run AFTER package
installation on every OS family, otherwise a v3-shaped config can be written
for a 2.x console (or vice versa) and the service fails to start.
"""
import os

import pytest
import yaml

TASKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tasks')


def load_main_tasks():
    with open(os.path.join(TASKS_DIR, 'main.yml')) as f:
        return yaml.safe_load(f)


def include_index(tasks, task_file):
    """Return the index of the task that includes the given task file."""
    for i, task in enumerate(tasks):
        target = task.get('ansible.builtin.include_tasks') or task.get('include_tasks')
        if isinstance(target, dict):
            target = target.get('file', '')
        if target and task_file in target:
            return i
    raise AssertionError(f"no task in main.yml includes {task_file}")


class TestMainTaskOrder:

    def test_rpm_install_runs_before_configure(self):
        tasks = load_main_tasks()
        install_idx = include_index(tasks, 'install-console-rpm.yml')
        configure_idx = include_index(tasks, 'configure-console.yml')
        assert install_idx < configure_idx, (
            "install-console-rpm.yml must be included before configure-console.yml: "
            "the RPM install sets use_pre_v3_template from the actually-installed "
            "version when redpanda_version == 'latest', so configuring first can "
            "render the wrong config shape for the installed console"
        )

    def test_deb_install_runs_before_configure(self):
        tasks = load_main_tasks()
        install_idx = include_index(tasks, 'install-console-deb.yml')
        configure_idx = include_index(tasks, 'configure-console.yml')
        assert install_idx < configure_idx, (
            "install-console-deb.yml must be included before configure-console.yml "
            "for the same template-choice reason as the RPM path"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
