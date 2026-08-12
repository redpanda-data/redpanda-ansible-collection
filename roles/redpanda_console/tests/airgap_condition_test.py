"""Behavioral test for the enable_airgap gate on repository configuration.

`-e enable_airgap=false` on the CLI produces the STRING "false". A Jinja
identity test (`enable_airgap is false`) only matches the boolean False, so
the repository-configuration includes were skipped for CLI users and the
subsequent package install had no repository to pull from. The gate must
treat the string "false" as falsey (via | bool).

The include is tag-isolated: --tags selects only the repo include, and
--skip-tags suppresses the tasks inside the included file so no real
repository work runs in the container.
"""
import pytest
import ansible_runner

PLAYBOOK = '/app/tests/airgap_condition.yml'
INVENTORY = '/app/tests/inventory'


def run(os_family, include_tag, skip_tag, airgap_cli_value):
    with open(INVENTORY, 'w') as f:
        f.write('localhost ansible_connection=local')

    r = ansible_runner.run(
        playbook=PLAYBOOK,
        inventory=INVENTORY,
        extravars={'ansible_os_family': os_family},
        cmdline=(
            f'-e enable_airgap={airgap_cli_value} '
            f'--tags {include_tag} --skip-tags {skip_tag}'
        ),
        quiet=True,
    )

    included_files = []
    skipped_tasks = []
    for event in r.events:
        data = event.get('event_data', {})
        if event['event'] == 'playbook_on_include':
            included_files.append(data.get('included_file', ''))
        if event['event'] == 'runner_on_skipped':
            skipped_tasks.append(data.get('task', ''))
    return r.status, included_files, skipped_tasks


@pytest.mark.parametrize("os_family,include_tag,skip_tag,repo_file,task_name", [
    ('Debian', 'console_repo_deb', 'console_deb_repo_steps',
     'configure-deb-repository.yml', 'Configure Redpanda DEB Repository'),
    ('RedHat', 'console_repo_rpm', 'console_rpm_repo_steps',
     'configure-rpm-repository.yml', 'Configure Redpanda RPM Repository'),
])
class TestAirgapGate:

    def test_cli_string_false_reaches_repo_configuration(
            self, os_family, include_tag, skip_tag, repo_file, task_name):
        status, included, skipped = run(os_family, include_tag, skip_tag, 'false')
        assert status == 'successful'
        assert task_name not in skipped, (
            f"repo include was skipped even though enable_airgap=false was "
            f"passed on the CLI (string 'false' must be treated as falsey)"
        )
        assert any(repo_file in f for f in included), (
            f"{repo_file} was never included for enable_airgap=false (CLI string)"
        )

    def test_cli_string_true_skips_repo_configuration(
            self, os_family, include_tag, skip_tag, repo_file, task_name):
        status, included, skipped = run(os_family, include_tag, skip_tag, 'true')
        assert status == 'successful'
        assert not any(repo_file in f for f in included), (
            f"{repo_file} must not be included when airgapped"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
