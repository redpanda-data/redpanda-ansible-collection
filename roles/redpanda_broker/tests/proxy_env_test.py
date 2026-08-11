"""The proxied GPG-key import must use the same proxy variable it is gated
on: gating on https_proxy_value while exporting rpm_proxy means a user who
sets only https_proxy_value gets the 'with proxy' branch running with no
proxy at all, and the import hangs or fails."""
import pytest
import yaml


TASK_FILE = '/app/tasks/configure-rpm-repository.yml'


def test_proxied_gpg_import_uses_its_gate_variable():
    with open(TASK_FILE) as f:
        tasks = yaml.safe_load(f)

    proxied = [t for t in tasks
               if isinstance(t, dict) and t.get('name') == 'Install GPG key with proxy']
    assert proxied, "expected an 'Install GPG key with proxy' task"
    task = proxied[0]

    when = task.get('when', '')
    when_text = when if isinstance(when, str) else ' '.join(when)
    assert 'https_proxy_value' in when_text, \
        "the proxied import is expected to be gated on https_proxy_value"

    env = task.get('environment', {})
    assert 'https_proxy_value' in str(env.get('https_proxy', '')), \
        f"environment must export the gate variable https_proxy_value, got {env!r}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))