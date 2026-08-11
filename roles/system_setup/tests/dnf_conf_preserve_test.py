import os

import ansible_runner
import pytest


# Runs only the DNF proxy configuration task (node_deps_proxy tag); the dnf
# package install tasks never run in the container.
TAGS = 'node_deps_proxy'

DNF_CONF = '/etc/dnf/dnf.conf'

# Settings an operator (or the distro) already had in place before the role
# runs. The proxy task must add the proxy without destroying any of these.
PRESEEDED_CONF = """\
[main]
gpgcheck=1
keepcache=True
max_parallel_downloads=20
"""


def run(extravars):
    here = os.path.dirname(os.path.abspath(__file__))

    r = ansible_runner.run(
        playbook=os.path.join(here, 'pkg_proxy_test.yml'),
        inventory=os.path.join(here, 'inventory'),
        extravars=extravars,
        cmdline=f'--tags {TAGS}',
        quiet=False,
    )
    return r.status


class TestDnfConfPreserved:

    def setup_method(self, method):
        os.makedirs(os.path.dirname(DNF_CONF), exist_ok=True)
        with open(DNF_CONF, 'w') as f:
            f.write(PRESEEDED_CONF)

    def test_existing_settings_survive_proxy_configuration(self):
        status = run({
            'node_deps_flavor': 'rpm',
            'rpm_proxy': 'proxy.example.com:3128',
            'create_pkg_mgr_proxy': True,
        })
        assert status == 'successful'

        with open(DNF_CONF) as f:
            content = f.read()

        for line in ('gpgcheck=1', 'keepcache=True', 'max_parallel_downloads=20'):
            assert line in content, (
                f'pre-existing dnf.conf setting {line!r} was destroyed by the '
                f'proxy task; dnf.conf now reads:\n{content}'
            )
        assert 'proxy=http://proxy.example.com:3128' in content, (
            f'proxy setting missing from dnf.conf:\n{content}'
        )

    def test_proxy_configuration_is_idempotent(self):
        for _ in range(2):
            status = run({
                'node_deps_flavor': 'rpm',
                'rpm_proxy': 'proxy.example.com:3128',
                'create_pkg_mgr_proxy': True,
            })
            assert status == 'successful'

        with open(DNF_CONF) as f:
            content = f.read()
        assert content.count('proxy=http://proxy.example.com:3128') == 1, (
            f'proxy line duplicated in dnf.conf:\n{content}'
        )
        assert 'keepcache=True' in content


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))