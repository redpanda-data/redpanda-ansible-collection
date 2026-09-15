import os
import shutil
import tempfile

import pytest
import ansible_runner


INVENTORY = """\
[connect]
node1 ansible_connection=local
"""

OVERRIDE_CONTENT = """\
log4j.rootLogger=DEBUG, stdout
log4j.appender.stdout=org.apache.log4j.ConsoleAppender
log4j.appender.stdout.layout=org.apache.log4j.PatternLayout
# user-managed logging configuration
"""


class TestLog4jOverride:

    def test_override_survives_the_full_generator_sequence(self):
        """log4j_config_override_content must win the final log4j file.

        The jmx-exporter generator used to rewrite connect-log4j.properties
        gated on a different variable (logging_config_override_content), so
        running the role with the documented override still ended with the
        stock template on disk.
        """
        work_dir = tempfile.mkdtemp()
        inv = os.path.join(work_dir, 'inventory')
        with open(inv, 'w') as f:
            f.write(INVENTORY)
        config_dir = os.path.join(work_dir, 'config')

        try:
            r = ansible_runner.run(
                playbook='/app/tests/log4j_override.yml',
                inventory=inv,
                extravars={
                    'redpanda_user': 'redpanda',
                    'redpanda_group': 'redpanda',
                    'redpanda_connect_config_dir': config_dir,
                    'log4j_config_override_content': OVERRIDE_CONTENT,
                    # needed by the stock log4j template, which the old code
                    # renders over the override
                    'log4j_log_level': 'WARN',
                },
                quiet=False,
            )
            assert r.status == 'successful', f"Playbook failed: {r.rc}"

            with open(os.path.join(config_dir, 'connect-log4j.properties')) as f:
                final = f.read()
            assert final == OVERRIDE_CONTENT, \
                "the user-provided log4j override must be the final file content, " \
                f"got:\n{final}"

            # the jmx exporter config itself must still be produced
            assert os.path.exists(os.path.join(config_dir, 'jmx-exporter-config.json'))
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))