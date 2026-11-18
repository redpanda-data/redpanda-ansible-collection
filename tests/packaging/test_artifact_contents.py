"""The built collection artifact contains exactly the committed collection.

ansible-galaxy collection build packages the whole directory it is pointed
at and does not consult .gitignore, so a release machine's local state
(assistant settings holding session credentials, virtualenvs, IDE state,
CI logs, pytest caches, scratch files) ships to every Galaxy consumer
unless the build is fenced off from it.

Each test copies the collection's tracked files into a fresh git repository
and then plants the kind of local state a real release machine carries,
so the assertions hold for a dirty working tree rather than passing
trivially on a clean checkout.

Run from the collection root: python3 -m pytest tests/packaging -v
"""
import fnmatch
import os
import re
import shutil
import stat
import subprocess
import tarfile

import pytest

COLLECTION_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# A stand-in credential; the assertions look for it in every packaged file.
PLANTED_SECRET = 'ASIAPLANTEDDECOYKEY0'

# Local state a release machine carries that git does not track: ignored
# directories, ignored files, and plain untracked files.
PLANTED_FILES = {
    '.claude/settings.local.json':
        '{"permissions": {"allow": ["Bash(export AWS_ACCESS_KEY_ID=\\"%s\\")"]}}' % PLANTED_SECRET,
    '.claude/report.md.cld': 'notes %s' % PLANTED_SECRET,
    '.venv/bin/activate': 'export AWS_ACCESS_KEY_ID=%s' % PLANTED_SECRET,
    '.idea/workspace.xml': '<env name="AWS_ACCESS_KEY_ID" value="%s"/>' % PLANTED_SECRET,
    '.ansible/logs/build.log': 'AWS_ACCESS_KEY_ID=%s' % PLANTED_SECRET,
    '.logs/run.log': 'AWS_ACCESS_KEY_ID=%s' % PLANTED_SECRET,
    '.pytest_cache/v/cache/nodeids': PLANTED_SECRET,
    '.env': 'AWS_ACCESS_KEY_ID=%s' % PLANTED_SECRET,
    'roles/redpanda_broker/.pytest_cache/v/cache/nodeids': PLANTED_SECRET,
    'roles/redpanda_broker/tests/inventory': 'node1 secret=%s' % PLANTED_SECRET,
    'roles/redpanda_broker/tasks/.scratch.yml': PLANTED_SECRET,
    'roles/redpanda_broker/tasks/untracked_debug.yml': '# %s' % PLANTED_SECRET,
    'scratch-notes.md': PLANTED_SECRET,
}

# Written by ansible-galaxy into every artifact.
GENERATED_MEMBERS = {'MANIFEST.json', 'FILES.json'}

# Role test inventories name real hosts and their connection secrets, so most
# are gitignored; none of them, committed or not, belongs in the artifact.
ROLE_TEST_INVENTORY = 'roles/*/tests/inventory'

# A stand-in Galaxy API key; no make output may contain it.
PLANTED_TOKEN = 'planted-galaxy-token-0f3a9c'


def _ships(tracked_path):
    """Committed files that belong in the artifact.

    galaxy.yml is folded into MANIFEST.json rather than shipped, the
    repository's own tests/ tree is development tooling, and role test
    inventories are kept out whether or not they are committed.
    """
    return not (_is_dot_path(tracked_path)
                or tracked_path == 'galaxy.yml'
                or tracked_path.startswith('tests/')
                or fnmatch.fnmatch(tracked_path, ROLE_TEST_INVENTORY))


def _git(repo, *args):
    return subprocess.run(
        ['git', '-C', repo, *args], check=True, capture_output=True, text=True,
    ).stdout


def _is_dot_path(path):
    return any(part.startswith('.') for part in path.split('/'))


def _tracked_files():
    """Tracked files that exist in the working tree, as they stand now."""
    listed = _git(COLLECTION_ROOT, 'ls-files', '-z').split('\0')
    return sorted(p for p in listed if p and os.path.isfile(os.path.join(COLLECTION_ROOT, p)))


@pytest.fixture
def dirty_checkout(tmp_path):
    """A git repo holding the collection's tracked files plus untracked local state."""
    repo = tmp_path / 'collection'
    tracked = _tracked_files()
    for rel in tracked:
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(os.path.join(COLLECTION_ROOT, rel), dest)
    _git(str(repo), 'init', '-q')
    _git(str(repo), 'add', '-f', '--', *tracked)
    _git(str(repo), '-c', 'user.name=test', '-c', 'user.email=test@example.invalid',
         'commit', '-q', '-m', 'snapshot')
    for rel, content in PLANTED_FILES.items():
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
    # A stale artifact from an earlier build also sits in the tree.
    shutil.copy2(repo / 'galaxy.yml', repo / 'redpanda-cluster-0.0.0.tar.gz')
    return repo, tracked


def _read_artifact(outdir):
    tarballs = [f for f in os.listdir(outdir) if f.endswith('.tar.gz')]
    assert len(tarballs) == 1, f"expected exactly one artifact in {outdir}, found {tarballs}"
    members = {}
    with tarfile.open(os.path.join(outdir, tarballs[0])) as tar:
        for info in tar.getmembers():
            if info.isfile():
                members[info.name] = tar.extractfile(info).read()
    return members


def _assert_no_planted_state(members):
    dot_paths = sorted(n for n in members if _is_dot_path(n))
    assert not dot_paths, f"dot-paths shipped in the artifact: {dot_paths[:20]}"
    carrying_secret = sorted(n for n, data in members.items() if PLANTED_SECRET.encode() in data)
    assert not carrying_secret, f"planted credential shipped in: {carrying_secret}"


def test_release_build_ships_exactly_the_committed_collection(dirty_checkout, tmp_path):
    repo, tracked = dirty_checkout
    outdir = tmp_path / 'dist'
    subprocess.run(['make', '-C', str(repo), 'build', f'DIST_DIR={outdir}'],
                   check=True, capture_output=True, text=True)
    members = _read_artifact(outdir)

    _assert_no_planted_state(members)
    expected = {p for p in tracked if _ships(p)}
    shipped = set(members) - GENERATED_MEMBERS
    assert shipped == expected, (
        f"shipped but not committed: {sorted(shipped - expected)[:20]}; "
        f"committed but missing: {sorted(expected - shipped)[:20]}"
    )


def test_direct_build_of_a_dirty_tree_ships_no_dot_paths(dirty_checkout, tmp_path):
    """Backstop for anyone who runs ansible-galaxy directly instead of make build.

    Only make build fences off untracked files that are not dot-paths; a
    direct build is held to the weaker guarantee of shipping no dot-paths
    and no role test inventories.
    """
    repo, _ = dirty_checkout
    outdir = tmp_path / 'dist'
    subprocess.run(['ansible-galaxy', 'collection', 'build', '--output-path', str(outdir), str(repo)],
                   check=True, capture_output=True, text=True)
    members = _read_artifact(outdir)

    dot_paths = sorted(n for n in members if _is_dot_path(n))
    assert not dot_paths, f"dot-paths shipped in the artifact: {dot_paths[:20]}"
    for planted in PLANTED_FILES:
        if _is_dot_path(planted):
            assert planted not in members

    inventories = sorted(n for n in members if fnmatch.fnmatch(n, ROLE_TEST_INVENTORY))
    assert not inventories, f"role test inventories shipped in the artifact: {inventories}"


def _commit_all(repo, message):
    _git(str(repo), 'add', '-u')
    _git(str(repo), '-c', 'user.name=test', '-c', 'user.email=test@example.invalid',
         'commit', '-q', '-m', message)


def test_verify_artifact_fails_when_the_artifact_cannot_be_read(dirty_checkout, tmp_path):
    """A trailing comment on the version line is valid YAML, but the Makefile
    then derives an artifact name ansible-galaxy never wrote. The check must
    stop the release rather than report an unread artifact as clean.
    """
    repo, _ = dirty_checkout
    galaxy_yml = repo / 'galaxy.yml'
    commented, count = re.subn(r'(?m)^(version: *\S+)[ \t]*$', r'\1  # pinned', galaxy_yml.read_text())
    assert count == 1, "galaxy.yml no longer has a bare 'version: X' line to annotate"
    galaxy_yml.write_text(commented)
    _commit_all(repo, 'annotate version')

    result = subprocess.run(['make', '-C', str(repo), 'verify-artifact', f'DIST_DIR={tmp_path / "dist"}'],
                            capture_output=True, text=True)

    assert result.returncode != 0, (
        f"verify-artifact passed an artifact it could not list:\n{result.stdout}{result.stderr}"
    )
    assert 'no dot-paths' not in result.stdout


def test_publish_does_not_print_the_api_key(dirty_checkout, tmp_path):
    """make echoes each recipe line before running it, expanded variables
    included, so the upload line must be silenced or the key reaches the
    terminal scrollback and any CI log.
    """
    repo, _ = dirty_checkout
    real_galaxy = shutil.which('ansible-galaxy')
    assert real_galaxy, "ansible-galaxy must be on PATH to build the artifact"
    # Builds for real; the upload itself is swallowed so nothing leaves the machine.
    shim_dir = tmp_path / 'bin'
    shim_dir.mkdir()
    shim = shim_dir / 'ansible-galaxy'
    shim.write_text(
        '#!/bin/sh\n'
        'if [ "$1" = collection ] && [ "$2" = publish ]; then exit 0; fi\n'
        f'exec "{real_galaxy}" "$@"\n'
    )
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
    env = dict(os.environ, PATH=f"{shim_dir}{os.pathsep}{os.environ['PATH']}")

    result = subprocess.run(
        ['make', '-C', str(repo), 'publish', f'DIST_DIR={tmp_path / "dist"}',
         f'ANSIBLE_GALAXY_API_KEY={PLANTED_TOKEN}'],
        capture_output=True, text=True, env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert PLANTED_TOKEN not in result.stdout + result.stderr
