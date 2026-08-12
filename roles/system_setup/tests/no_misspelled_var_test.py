import os

import pytest


# The role once shipped a misspelled variable name (redpanda with the d and p
# transposed) and later a back-compat shim honoring it. The shim has been
# removed; this structural test keeps the misspelling from ever reappearing
# anywhere in the role tree. The token is assembled so this file cannot match
# itself in ad-hoc greps.
MISSPELLING = 'repd' + 'anda'

SKIP_DIRS = {'.git', '__pycache__', '.pytest_cache', 'artifacts', 'env', '.venv'}


def test_misspelled_variable_absent_from_role_tree():
    role_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    this_file = os.path.abspath(__file__)

    offenders = []
    for dirpath, dirnames, filenames in os.walk(role_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            if os.path.abspath(path) == this_file:
                continue
            try:
                with open(path, encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except (OSError, IsADirectoryError):
                continue
            if MISSPELLING in content:
                offenders.append(os.path.relpath(path, role_root))

    assert not offenders, (
        f'misspelled variable name {MISSPELLING!r} found in: {offenders}; '
        'the back-compat shim was removed and the misspelling must not return'
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))