import os

import ansible_runner
import pytest


# Runs only the package-manager proxy configuration task from the
# install-node-deps task files; the apt/dnf install tasks are excluded by the
# tag filter and never run in the container.
TAGS = 'node_deps_proxy'

APT_PROXY_TASK = 'Node dependencies - Set APT proxy'
DNF_PROXY_TASK = 'Node dependencies - Set DNF proxy'

APT_PROXY_CONF = '/etc/apt/apt.conf.d/proxy.conf'
DNF_CONF = '/etc/dnf/dnf.conf'


def run(extravars):
    here = os.path.dirname(os.path.abspath(__file__))

    r = ansible_runner.run(
        playbook=os.path.join(here, 'pkg_proxy_test.yml'),
        inventory=os.path.join(here, 'inventory'),
        extravars=extravars,
        cmdline=f'--tags {TAGS}',
        quiet=False,
    )

    # Map task name -> final runner event type (ok/skipped/failed).
    outcomes = {}
    for event in r.events:
        if event['event'] in ('runner_on_ok', 'runner_on_skipped', 'runner_on_failed'):
            task = event.get('event_data', {}).get('task')
            outcomes[task] = event['event']

    return r.status, outcomes


class TestProxyFlagTruthiness:

    def test_apt_proxy_written_with_string_flag(self):
        # INI inventories and -e pass booleans as strings; "yes" must enable
        # the proxy. The old `is true` identity test silently skipped it.
        if os.path.exists(APT_PROXY_CONF):
            os.remove(APT_PROXY_CONF)
        status, outcomes = run({
            'node_deps_flavor': 'deb',
            'https_proxy_value': 'proxy.example.com:3128',
            'create_pkg_mgr_proxy': 'yes',
        })
        assert status == 'successful'
        assert outcomes.get(APT_PROXY_TASK) == 'runner_on_ok', (
            f'expected the APT proxy task to run, got {outcomes}'
        )
        with open(APT_PROXY_CONF) as f:
            content = f.read()
        assert 'proxy.example.com:3128' in content

    def test_dnf_proxy_written_with_string_flag(self):
        os.makedirs(os.path.dirname(DNF_CONF), exist_ok=True)
        with open(DNF_CONF, 'w') as f:
            f.write('[main]\ngpgcheck=1\n')
        status, outcomes = run({
            'node_deps_flavor': 'rpm',
            'rpm_proxy': 'proxy.example.com:3128',
            'create_pkg_mgr_proxy': 'yes',
        })
        assert status == 'successful'
        assert outcomes.get(DNF_PROXY_TASK) == 'runner_on_ok', (
            f'expected the DNF proxy task to run, got {outcomes}'
        )
        with open(DNF_CONF) as f:
            content = f.read()
        assert 'proxy.example.com:3128' in content

    def test_apt_proxy_skipped_when_flag_disabled(self):
        status, outcomes = run({
            'node_deps_flavor': 'deb',
            'https_proxy_value': 'proxy.example.com:3128',
            'create_pkg_mgr_proxy': False,
        })
        assert status == 'successful'
        assert outcomes.get(APT_PROXY_TASK) == 'runner_on_skipped', (
            f'expected the APT proxy task to be skipped, got {outcomes}'
        )

    def test_apt_proxy_skipped_on_gcp(self):
        status, outcomes = run({
            'node_deps_flavor': 'deb',
            'https_proxy_value': 'proxy.example.com:3128',
            'create_pkg_mgr_proxy': True,
            'using_gcp': 'true',
        })
        assert status == 'successful'
        assert outcomes.get(APT_PROXY_TASK) == 'runner_on_skipped', (
            f'expected the APT proxy task to be skipped on GCP, got {outcomes}'
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
