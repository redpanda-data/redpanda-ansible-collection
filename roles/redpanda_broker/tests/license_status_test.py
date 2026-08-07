import os
import stat
import tempfile
import shutil

import pytest
import ansible_runner


TAGS = 'broker_check_license_status,broker_license_needed'

MOCK_RPK_TEMPLATE = """\
#!/bin/bash
cat <<'OUTPUT'
LICENSE INFORMATION
===================
Organization:      test-org
Type:              enterprise
Expires:           2027-01-01
Status:            {status}
OUTPUT
exit {rc}
"""


def run_playbook(status_line, rc=0):
    inventory_path = '/app/tests/inventory'
    with open(inventory_path, 'w') as f:
        f.write('localhost ansible_connection=local')

    mock_dir = tempfile.mkdtemp()
    mock_path = os.path.join(mock_dir, 'rpk')
    with open(mock_path, 'w') as f:
        f.write(MOCK_RPK_TEMPLATE.format(status=status_line, rc=rc))
    os.chmod(mock_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    try:
        r = ansible_runner.run(
            playbook='/app/tests/license_status.yml',
            inventory=inventory_path,
            cmdline=f'--tags {TAGS}',
            envvars={'PATH': f"{mock_dir}:{os.environ.get('PATH', '')}"},
            quiet=False
        )
        assert r.status == 'successful', f"Playbook failed: {r.rc}"

        for event in r.events:
            if event['event'] == 'runner_on_ok':
                facts = event['event_data']['res'].get('ansible_facts', {})
                if 'redpanda_license_loaded' in facts:
                    return facts['redpanda_license_loaded']

        raise ValueError("Could not find redpanda_license_loaded in playbook output")
    finally:
        shutil.rmtree(mock_dir)


@pytest.mark.parametrize("status_line,rc,expected", [
    ('valid', 0, True),
    # 'valid' is a substring of 'invalid'; the check must not treat an
    # invalid or not-valid license as loaded, or license application is
    # skipped and enterprise features silently stay off
    ('invalid', 0, False),
    ('not valid', 0, False),
    ('expired', 0, False),
    # rpk itself failing must not count as loaded
    ('valid', 1, False),
])
def test_license_loaded(status_line, rc, expected):
    loaded = run_playbook(status_line, rc)
    assert bool(loaded) == expected, \
        f"Status: {status_line} (rc={rc}): expected loaded={expected}, got {loaded}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
