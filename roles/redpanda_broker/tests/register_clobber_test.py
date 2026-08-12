"""Guard against register-clobbering between conditional twin tasks.

Ansible registers a result for skipped tasks too. When two tasks in the same
file register the same variable and are gated by mutually exclusive `when`
clauses, whichever twin is skipped *after* the real one overwrites the real
result with a skipped-task stub. That pattern silently disabled restart
detection on SASL clusters and the SASL bootstrap stop for pinned pre-24.2
installs, so any duplicate register within a task file is treated as a
defect.
"""
import glob
import os

import pytest
import yaml


TASKS_DIR = '/app/tasks'


def iter_tasks(tasks):
    for task in tasks or []:
        if not isinstance(task, dict):
            continue
        yield task
        for section in ('block', 'rescue', 'always'):
            if section in task:
                yield from iter_tasks(task[section])


def registers_in_file(path):
    with open(path) as f:
        tasks = yaml.safe_load(f)
    names = []
    for task in iter_tasks(tasks):
        if 'register' in task:
            names.append(task['register'])
    return names


@pytest.mark.parametrize(
    "task_file",
    sorted(glob.glob(os.path.join(TASKS_DIR, '*.yml'))),
    ids=os.path.basename,
)
def test_no_duplicate_registers(task_file):
    names = registers_in_file(task_file)
    duplicates = sorted({n for n in names if names.count(n) > 1})
    assert not duplicates, (
        f"{os.path.basename(task_file)} registers {duplicates} from more than "
        f"one task; a skipped conditional twin overwrites the real result"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))