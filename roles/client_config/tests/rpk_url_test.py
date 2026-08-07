import pytest
import ansible_runner
import yaml


def computed_url(extravars):
    inv = '/app/tests/inventory'
    with open(inv, 'w') as f:
        f.write('localhost ansible_connection=local')
    r = ansible_runner.run(
        playbook='/app/tests/rpk_url.yml',
        inventory=inv,
        extravars=extravars,
        cmdline='--tags client_rpk_url',
        quiet=False,
    )
    assert r.status == 'successful', f"playbook failed: {r.rc}"
    for event in r.events:
        if event['event'] == 'runner_on_ok':
            res = event['event_data'].get('res', {})
            if 'rpk_download_url' in res:
                return res['rpk_download_url']
            facts = res.get('ansible_facts', {})
            if 'rpk_download_url' in facts:
                return facts['rpk_download_url']
    raise ValueError('rpk_download_url not found in output')


@pytest.mark.parametrize("extravars,expected", [
    # default: latest for the host architecture
    ({'ansible_architecture': 'x86_64'},
     'https://github.com/redpanda-data/redpanda/releases/latest/download/rpk-linux-amd64.zip'),
    ({'ansible_architecture': 'aarch64'},
     'https://github.com/redpanda-data/redpanda/releases/latest/download/rpk-linux-arm64.zip'),
    # pinned version
    ({'ansible_architecture': 'x86_64', 'rpk_version': 'v24.3.1'},
     'https://github.com/redpanda-data/redpanda/releases/download/v24.3.1/rpk-linux-amd64.zip'),
    # mirror via rpk_base_url must take effect (it was previously dead)
    ({'ansible_architecture': 'x86_64', 'rpk_base_url': 'https://mirror.example.com/releases'},
     'https://mirror.example.com/releases/latest/download/rpk-linux-amd64.zip'),
    # full-URL override wins over everything
    ({'ansible_architecture': 'x86_64', 'rpk_url': 'https://example.com/custom-rpk.zip'},
     'https://example.com/custom-rpk.zip'),
])
def test_rpk_download_url(extravars, expected):
    assert computed_url(extravars) == expected


def test_cert_install_runs_privileged():
    # /opt/rpk/certs creation needs escalation like the sibling rpk install
    with open('/app/tasks/install-cert.yml') as f:
        tasks = yaml.safe_load(f)
    unprivileged = [t.get('name') for t in tasks
                    if isinstance(t, dict) and not t.get('become')]
    assert not unprivileged, \
        f"install-cert tasks must use become: {unprivileged}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
