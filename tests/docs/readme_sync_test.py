"""Any role that declares an argument spec must carry the generated
variable table in its README, and the table must match the spec. This is
what keeps role documentation from drifting away from the validated
inputs (six role READMEs previously documented none of their variables,
or variables that did not exist)."""
import os
import subprocess

import pytest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def test_role_readmes_in_sync_with_argument_specs():
    result = subprocess.run(
        ['python3', os.path.join(REPO_ROOT, 'scripts', 'generate-role-docs.py'), '--check'],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, \
        f"role READMEs out of sync with their argument specs:\n{result.stderr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
