"""Behavioral test for is_using_unstable channel selection.

The role's defaults advertise unstable-channel variables, but the repo
task files computed their *_actual facts from the stable variables
unconditionally, so setting is_using_unstable: true was silently ignored
and hosts were pointed at the stable channel. The fact computation must
select stable vs unstable URLs, keyring paths and repo names based on
is_using_unstable, mirroring the broker role.

Only the fact-computation tasks run here: --skip-tags suppresses the
tasks that would do real repository work in the container.
"""
import pytest
import ansible_runner

PLAYBOOK = '/app/tests/unstable_repo.yml'
INVENTORY = '/app/tests/inventory'
SKIP_TAGS = 'console_deb_repo_steps,console_rpm_repo_steps'


def compute_repo_facts(is_using_unstable):
    with open(INVENTORY, 'w') as f:
        f.write('localhost ansible_connection=local')

    r = ansible_runner.run(
        playbook=PLAYBOOK,
        inventory=INVENTORY,
        extravars={'is_using_unstable': is_using_unstable},
        cmdline=f'--skip-tags {SKIP_TAGS}',
        quiet=True,
    )
    assert r.status == 'successful', f"fact computation failed: {r.status}"

    facts = {}
    for event in r.events:
        if event['event'] == 'runner_on_ok':
            res = event.get('event_data', {}).get('res', {})
            facts.update(res.get('ansible_facts', {}))
    return facts


class TestUnstableChannelSelection:

    def test_unstable_true_selects_unstable_channel(self):
        facts = compute_repo_facts(True)
        assert 'redpanda-unstable-yum' in facts.get('rp_standard_rpm_actual', ''), facts
        assert 'redpanda-unstable-yum' in facts.get('rp_noarch_rpm_actual', ''), facts
        assert 'redpanda-unstable-yum' in facts.get('rp_key_rpm_metadata_actual', ''), facts
        assert facts.get('repo_name_prefix') == 'redpanda-redpanda-unstable', facts
        assert 'redpanda-unstable-apt' in facts.get('rp_repo_signing_deb_actual', ''), facts
        assert 'unstable' in facts.get('rp_key_path_deb_actual', ''), facts

    def test_unstable_false_selects_stable_channel(self):
        facts = compute_repo_facts(False)
        assert 'unstable' not in facts.get('rp_standard_rpm_actual', 'MISSING'), facts
        assert 'redpanda-yum' in facts.get('rp_standard_rpm_actual', ''), facts
        assert facts.get('repo_name_prefix') == 'redpanda-redpanda', facts
        assert 'redpanda-apt main' in facts.get('rp_repo_signing_deb_actual', ''), facts
        assert 'unstable' not in facts.get('rp_key_path_deb_actual', 'MISSING'), facts


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
