import pytest
import ansible_runner


def run_playbook(extravars):
    inventory_path = '/app/tests/inventory'
    with open(inventory_path, 'w') as f:
        f.write('localhost ansible_connection=local')

    r = ansible_runner.run(
        playbook='/app/tests/version_assert.yml',
        inventory=inventory_path,
        extravars=extravars,
        cmdline='--tags broker_assert_version',
        quiet=False
    )

    failure_msg = None
    for event in r.events:
        if event['event'] == 'runner_on_failed':
            failure_msg = event['event_data']['res'].get('msg', '')
    return r.status, failure_msg


class TestVersionAssert:

    def test_defined_version_passes(self):
        status, _ = run_playbook({'redpanda_version': '24.3.1-1'})
        assert status == 'successful'

    def test_undefined_version_fails_with_actionable_message(self):
        status, msg = run_playbook({})
        assert status == 'failed'
        # the user must see the assert's fail_msg, not a raw Jinja
        # undefined-variable traceback
        assert "Variable 'redpanda_version' must be defined!" in (msg or ''), \
            f"expected the assert fail_msg, got: {msg!r}"

    def test_empty_version_fails_with_actionable_message(self):
        status, msg = run_playbook({'redpanda_version': ''})
        assert status == 'failed'
        assert "Variable 'redpanda_version' must be defined!" in (msg or '')


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))