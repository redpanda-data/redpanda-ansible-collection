"""Build the collection artifact and assert its contents.

ansible-galaxy collection build packages the working tree; without a
build_ignore manifest it ships development scaffolding (Dockerfiles, tests,
IDE state, virtualenvs) to every Galaxy consumer, and without a
dependencies map a bare ansible-core install fails at runtime on the
community.general / ansible.posix modules the roles use.

Run from the collection root: python3 -m pytest tests/packaging/ -v
"""
import json
import os
import subprocess
import tarfile
import tempfile

import pytest
import yaml


COLLECTION_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


@pytest.fixture(scope='module')
def artifact():
    with tempfile.TemporaryDirectory() as outdir:
        subprocess.run(
            ['ansible-galaxy', 'collection', 'build', '--output-path', outdir, COLLECTION_ROOT],
            check=True, capture_output=True, text=True,
        )
        tarballs = [f for f in os.listdir(outdir) if f.endswith('.tar.gz')]
        assert len(tarballs) == 1
        with tarfile.open(os.path.join(outdir, tarballs[0])) as tar:
            names = tar.getnames()
            manifest = json.load(tar.extractfile('MANIFEST.json'))
        yield names, manifest


FORBIDDEN_PATTERNS = [
    'Dockerfile',
    'docker-compose.yml',
    '/tests/',           # role test trees
    '.run/',
    '.buildkite/',
    '.github/',
    'library/mock_ansible_module.py',
    '.venv/',
    '.ansible/',
    '.idea/',
    '.logs/',
    '.claude/',
    'Makefile',
]


class TestArtifactContents:

    def test_no_development_scaffolding_ships(self, artifact):
        names, _ = artifact
        offenders = sorted({
            name for name in names
            for pattern in FORBIDDEN_PATTERNS
            if pattern in name
        })
        assert not offenders, \
            f"development scaffolding must not ship in the collection artifact: {offenders[:20]}"

    def test_runtime_collection_dependencies_declared(self, artifact):
        _, manifest = artifact
        deps = manifest['collection_info'].get('dependencies') or {}
        for needed in ('community.general', 'ansible.posix'):
            assert needed in deps, \
                f"roles use {needed} modules; galaxy.yml must declare the dependency"

    def test_repository_urls_point_at_this_repo(self, artifact):
        _, manifest = artifact
        info = manifest['collection_info']
        assert 'redpanda-ansible-collection' in (info.get('repository') or ''), \
            f"repository URL points elsewhere: {info.get('repository')}"
        assert 'redpanda-ansible-collection' in (info.get('issues') or ''), \
            f"issues URL points elsewhere: {info.get('issues')}"

    def test_has_a_required_galaxy_tag(self, artifact):
        _, manifest = artifact
        tags = set(manifest['collection_info'].get('tags') or [])
        required = {'application', 'cloud', 'database', 'eda', 'infrastructure',
                    'linux', 'monitoring', 'networking', 'security', 'storage',
                    'tools', 'windows'}
        assert tags & required, \
            f"galaxy requires at least one standard tag, got {sorted(tags)}"


def test_gitignore_covers_local_junk():
    with open(os.path.join(COLLECTION_ROOT, '.gitignore')) as f:
        gitignore = f.read()
    for needed in ('.venv', '.pytest_cache', '.logs', '.run'):
        assert needed in gitignore, f".gitignore must cover {needed}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
