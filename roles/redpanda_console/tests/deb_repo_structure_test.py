"""Structural tests over tasks/configure-deb-repository.yml.

The "Add Redpanda DEB repository (source)" task wrote to the SAME dest as
the binary-repo task and rendered the same binary content variable, so the
second copy silently overwrote the first and no deb-src line was ever
configured. The dead task and its never-used rp_repo_signing_src_deb
variables are removed rather than fixed: deb-src serves source packages,
which this role has no use for.
"""
import glob
import os

import pytest
import yaml

ROLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DEB_REPO_FILE = os.path.join(ROLE_DIR, 'tasks', 'configure-deb-repository.yml')


def load_tasks(path):
    with open(path) as f:
        return yaml.safe_load(f)


class TestDebRepoStructure:

    def test_no_two_tasks_write_the_same_dest(self):
        dests = []
        for task in load_tasks(DEB_REPO_FILE):
            for module in ('ansible.builtin.copy', 'copy',
                           'ansible.builtin.template', 'template',
                           'ansible.builtin.get_url', 'get_url'):
                args = task.get(module)
                if isinstance(args, dict) and 'dest' in args:
                    dests.append((task.get('name'), args['dest']))
        seen = {}
        for name, dest in dests:
            assert dest not in seen, (
                f"tasks {seen[dest]!r} and {name!r} both write to {dest}: "
                f"the later task silently overwrites the earlier one"
            )
            seen[dest] = name

    def test_no_dangling_deb_src_variables(self):
        role_yaml = (
            glob.glob(os.path.join(ROLE_DIR, 'tasks', '*.yml'))
            + glob.glob(os.path.join(ROLE_DIR, 'defaults', '*.yml'))
            + glob.glob(os.path.join(ROLE_DIR, 'vars', '*.yml'))
        )
        offenders = []
        for path in role_yaml:
            with open(path) as f:
                if 'rp_repo_signing_src_deb' in f.read():
                    offenders.append(os.path.relpath(path, ROLE_DIR))
        assert not offenders, (
            f"rp_repo_signing_src_deb* variables are dead (the deb-src task "
            f"never worked and was removed) but are still referenced in: {offenders}"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
