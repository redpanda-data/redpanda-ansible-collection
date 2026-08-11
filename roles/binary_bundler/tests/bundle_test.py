import os
import subprocess
import tarfile
import tempfile

import pytest
import ansible_runner


def run(extravars):
    inv = '/app/tests/inventory'
    with open(inv, 'w') as f:
        f.write('localhost ansible_connection=local')
    r = ansible_runner.run(
        playbook='/app/tests/bundle.yml',
        inventory=inv,
        extravars=extravars,
        quiet=False,
    )
    return r


def computed_urls(extravars):
    r = run(extravars)
    assert r.status == 'successful', f"playbook failed: {r.rc}"
    for event in r.events:
        if event['event'] == 'runner_on_ok':
            res = event['event_data'].get('res', {})
            if isinstance(res.get('msg'), dict) and 'deb' in res['msg']:
                return res['msg']
    raise ValueError('urls not found')


BASE_VARS = {'redpanda_version': '24.3.1-1', 'basearch': 'x86_64',
             'rpm_or_deb': 'deb'}


class TestUrlConstruction:

    def test_deb_urls_use_debian_arch(self):
        urls = computed_urls(BASE_VARS)
        for name, url in urls['deb'].items():
            assert url.endswith('_amd64.deb'), \
                f"{name}: Debian packages are amd64, never x86_64: {url}"

    def test_deb_arm(self):
        urls = computed_urls({**BASE_VARS, 'basearch': 'aarch64'})
        for name, url in urls['deb'].items():
            assert url.endswith('_arm64.deb'), f"{name}: {url}"

    def test_double_digit_minor_is_post_split(self):
        urls = computed_urls({**BASE_VARS, 'redpanda_version': '24.10.1-1'})
        assert len(urls['deb']) == 3, \
            "24.10 is after the package split; rpk and tuner must be bundled"

    def test_rpm_class_suffixes(self):
        urls = computed_urls(BASE_VARS)
        for name, url in urls['rpm_standard'].items():
            assert url.endswith('.x86_64.rpm'), f"{name}: {url}"
        for name, url in urls['rpm_noarch'].items():
            assert url.endswith('.noarch.rpm'), \
                f"{name}: noarch packages carry a noarch suffix, not the host arch: {url}"
        for name, url in urls['rpm_source'].items():
            assert url.endswith('.src.rpm'), \
                f"{name}: source packages carry a src suffix, not the host arch: {url}"


class TestDebBundleRun:

    def test_bundle_isolated_from_preexisting_tmp_files(self):
        fixtures = tempfile.mkdtemp()
        for pkg in ('redpanda', 'redpanda-rpk', 'redpanda-tuner'):
            pkg_dir = os.path.join(fixtures, 'apt/pool/main/r', pkg)
            os.makedirs(pkg_dir)
            with open(os.path.join(pkg_dir, f'{pkg}_24.3.1-1_amd64.deb'), 'w') as f:
                f.write(f'fixture {pkg}\n')

        decoy = '/tmp/redpanda-decoy.deb'
        with open(decoy, 'w') as f:
            f.write('unrelated pre-existing file\n')

        r = run({**BASE_VARS, 'run_bundle': True,
                 'redpanda_base_url': f'file://{fixtures}'})
        assert r.status == 'successful', f"bundle run failed: {r.rc}"

        assert os.path.exists(decoy), \
            "bundling must not delete unrelated files from the download directory"
        tarball = '/tmp/redpanda_debs.tar.gz'
        assert os.path.exists(tarball)
        with tarfile.open(tarball) as tar:
            names = [os.path.basename(n) for n in tar.getnames()]
        assert 'redpanda-decoy.deb' not in names, \
            f"unrelated files must not be swept into the tarball: {names}"
        assert 'redpanda_24.3.1-1_amd64.deb' in names, names


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))