"""Two tasks writing different content to the same dest can only fight:
the second write silently overwrites the first (or, as with the deb-src
task, was a copy-paste of the first and never did what its name claimed)."""
import glob
import os

import pytest
import yaml


TASKS_DIR = '/app/tasks'


def file_write_dests(path):
    with open(path) as f:
        tasks = yaml.safe_load(f)
    dests = []
    for task in tasks or []:
        if not isinstance(task, dict):
            continue
        for module in ('ansible.builtin.copy', 'copy',
                       'ansible.builtin.template', 'template'):
            args = task.get(module)
            if isinstance(args, dict) and 'dest' in args:
                dests.append(args['dest'])
    return dests


@pytest.mark.parametrize(
    "task_file",
    sorted(glob.glob(os.path.join(TASKS_DIR, '*.yml'))),
    ids=os.path.basename,
)
def test_no_duplicate_write_destinations(task_file):
    dests = file_write_dests(task_file)
    duplicates = sorted({d for d in dests if dests.count(d) > 1})
    # start-redpanda legitimately writes redpanda.yaml twice (first-run and
    # post-bootstrap check_mode probe) -- mutually exclusive on
    # is_initialized
    if os.path.basename(task_file) == 'start-redpanda.yml':
        duplicates = [d for d in duplicates if d != '/etc/redpanda/redpanda.yaml']
    assert not duplicates, (
        f"{os.path.basename(task_file)} writes {duplicates} from more than one "
        f"task; the later write silently clobbers the earlier one"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))