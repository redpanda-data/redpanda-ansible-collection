#!/usr/bin/env python3
"""Render each role's variable table from meta/argument_specs.yml into its
README between the AUTOGEN markers.

Usage: python3 scripts/generate-role-docs.py [--check]

--check exits non-zero if any README is out of date instead of rewriting it
(used by the docs drift test / CI).
"""
import argparse
import os
import sys

import yaml


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BEGIN = '<!-- BEGIN ROLE VARIABLES (generated from meta/argument_specs.yml; run scripts/generate-role-docs.py) -->'
END = '<!-- END ROLE VARIABLES -->'


def render_table(spec):
    main = spec['argument_specs']['main']
    lines = [
        BEGIN,
        '',
        '| Variable | Type | Default | Choices | Description |',
        '|---|---|---|---|---|',
    ]
    for name, opt in (main.get('options') or {}).items():
        typ = opt.get('type', 'str')
        if typ == 'list' and opt.get('elements'):
            typ = f"list of {opt['elements']}"
        default = opt.get('default', '')
        if opt.get('required'):
            default = '*required*'
        elif default == '':
            default = '—'
        else:
            default = f"`{default}`"
        choices = ', '.join(f'`{c}`' for c in opt.get('choices', [])) or '—'
        desc = ' '.join((opt.get('description') or []))
        desc = desc.replace('C(', '`').replace(')', '`') if 'C(' in desc else desc
        desc = desc.replace('|', '\\|')
        lines.append(f"| `{name}` | {typ} | {default} | {choices} | {desc} |")
    lines += ['', 'Variables not listed here are undeclared in the argument spec; see `defaults/main.yml`.', '', END]
    return '\n'.join(lines)


def process_role(role_dir, check):
    spec_path = os.path.join(role_dir, 'meta', 'argument_specs.yml')
    readme_path = os.path.join(role_dir, 'README.md')
    if not (os.path.isfile(spec_path) and os.path.isfile(readme_path)):
        return None
    with open(spec_path) as f:
        spec = yaml.safe_load(f)
    with open(readme_path) as f:
        readme = f.read()
    if BEGIN not in readme or END not in readme:
        return f"{readme_path}: missing AUTOGEN markers"
    head, rest = readme.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    updated = head + render_table(spec) + tail
    if updated != readme:
        if check:
            return f"{readme_path}: out of date with meta/argument_specs.yml"
        with open(readme_path, 'w') as f:
            f.write(updated)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()

    problems = []
    roles_dir = os.path.join(REPO_ROOT, 'roles')
    for role in sorted(os.listdir(roles_dir)):
        problem = process_role(os.path.join(roles_dir, role), args.check)
        if problem:
            problems.append(problem)
    for p in problems:
        print(p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
