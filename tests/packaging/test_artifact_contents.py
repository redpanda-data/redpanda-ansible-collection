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
import os
import shutil
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


def _ships(tracked_path):
    """Committed files that belong in the artifact.

    galaxy.yml is folded into MANIFEST.json rather than shipped, and the
    repository's own tests/ tree is development tooling.
    """
    return not (_is_dot_path(tracked_path)
                or tracked_path == 'galaxy.yml'
                or tracked_path.startswith('tests/'))


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
    direct build is held to the weaker guarantee of shipping no dot-paths.
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
