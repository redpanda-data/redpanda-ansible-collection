import json
import os
import shutil
import stat
import tempfile

import pytest
import ansible_runner
import yaml


TAGS = 'broker_check_license_status,broker_license_needed,broker_set_license_string'

SENTINEL = 'SENTINEL-LICENSE-KEY-DO-NOT-LOG'

# license info reports invalid so the set path runs; license set succeeds
MOCK_RPK = """\
#!/bin/bash
if [ "$1 $2 $3" = "cluster license info" ]; then
  echo "Status: invalid"
  exit 0
fi
echo "Successfully uploaded license."
"""


def run_events_blob():
    inventory_path = '/app/tests/inventory'
    with open(inventory_path, 'w') as f:
        f.write('localhost ansible_connection=local')

    mock_dir = tempfile.mkdtemp()
    mock_path = os.path.join(mock_dir, 'rpk')
    with open(mock_path, 'w') as f:
        f.write(MOCK_RPK)
    os.chmod(mock_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    try:
        r = ansible_runner.run(
            playbook='/app/tests/license_status.yml',
            inventory=inventory_path,
            extravars={'redpanda_license': SENTINEL},
            cmdline=f'--tags {TAGS}',
            envvars={'PATH': f"{mock_dir}:{os.environ.get('PATH', '')}"},
            quiet=False
        )
        assert r.status == 'successful', f"Playbook failed: {r.rc}"
        blob = ''
        try:
            blob += r.stdout.read()
        except Exception:
            pass
        for event in r.events:
            blob += json.dumps(event, default=str)
        return blob
    finally:
        shutil.rmtree(mock_dir)


def test_license_string_never_appears_in_output():
    # At default verbosity a secret placed on a command line is recorded in
    # the task invocation of every run's events (and any CI log shipping
    # them). The enterprise license must therefore never be passed as an
    # rpk argument.
    blob = run_events_blob()
    assert SENTINEL not in blob, \
        "the license string leaked into playbook output/events"


def test_cloudsmith_token_tasks_are_no_log():
    # The nightly-install tasks interpolate cloudsmith_token into URLs that
    # land in module args (get_url/rpm_key/apt repo content) and therefore
    # in events at default verbosity; they must carry no_log. Structural
    # check because exercising them would download from the real CDN.
    offenders = []
    for path in ('/app/tasks/install-nightly-build-deb.yml',
                 '/app/tasks/install-nightly-build-rpm.yml'):
        with open(path) as f:
            tasks = yaml.safe_load(f)
        for task in tasks or []:
            if not isinstance(task, dict):
                continue
            text = json.dumps(task)
            if ('cloudsmith_token' in text or 'cloudsmith_gpg_key_url' in text
                    or 'nightly_repo_url' in text):
                if 'no_log' not in task:
                    offenders.append(f"{os.path.basename(path)}: {task.get('name')}")
    assert not offenders, \
        f"tasks interpolating the Cloudsmith token must set no_log: {offenders}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
