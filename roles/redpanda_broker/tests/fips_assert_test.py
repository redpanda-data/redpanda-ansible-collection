import os
import stat

import pytest
import ansible_runner


FIPS_MODE_SETUP = '/usr/bin/fips-mode-setup'

# fips-mode-setup --is-enabled exit codes: 0 enabled, 1 inconsistent, 2 disabled
MOCK_TEMPLATE = """\
#!/bin/bash
exit {rc}
"""


def run_playbook(os_fips_rc, fips_mode, os_family='RedHat'):
    inventory_path = '/app/tests/inventory'
    with open(inventory_path, 'w') as f:
        f.write('localhost ansible_connection=local')

    # The role invokes fips-mode-setup by absolute path, so the mock must
    # shadow it at /usr/bin (the test container has no real one).
    assert not os.path.exists(FIPS_MODE_SETUP) or os.path.getsize(FIPS_MODE_SETUP) < 100, \
        "refusing to overwrite a real fips-mode-setup"
    with open(FIPS_MODE_SETUP, 'w') as f:
        f.write(MOCK_TEMPLATE.format(rc=os_fips_rc))
    os.chmod(FIPS_MODE_SETUP, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    try:
        r = ansible_runner.run(
            playbook='/app/tests/fips_assert.yml',
            inventory=inventory_path,
            extravars={
                'fips_mode': fips_mode,
                'ansible_os_family': os_family,
            },
            quiet=False
        )
        return r.status
    finally:
        os.remove(FIPS_MODE_SETUP)


@pytest.mark.parametrize("os_fips_rc,fips_mode,expected_status", [
    # OS FIPS enabled + role fips_mode enabled: the supported FIPS deployment,
    # must pass
    (0, 'enabled', 'successful'),
    # OS FIPS disabled but role wants FIPS: must fail (redpanda would fail to
    # start)
    (2, 'enabled', 'failed'),
    # OS FIPS inconsistent while role wants FIPS: must fail
    (1, 'enabled', 'failed'),
    # OS FIPS disabled with permissive bypass: documented escape hatch, must
    # pass
    (2, 'permissive', 'successful'),
])
def test_fips_assert(os_fips_rc, fips_mode, expected_status):
    status = run_playbook(os_fips_rc, fips_mode)
    assert status == expected_status, \
        f"rc={os_fips_rc} fips_mode={fips_mode}: expected {expected_status}, got {status}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
