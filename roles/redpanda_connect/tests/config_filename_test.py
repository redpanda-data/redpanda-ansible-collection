import os
import shutil
import tempfile

import pytest
import ansible_runner


INVENTORY = """\
[redpanda]
node1 ansible_connection=local

[connect]
node1 ansible_connection=local
"""

UNIT_PATH = '/etc/systemd/system/redpanda-connect.service'


class TestConfigFilename:

    def test_overridden_config_file_name_is_written_and_referenced(self):
        """connect_distributed_config_file must drive the config write.

        The systemd unit's ExecStart already honors the variable; the
        generator used to hardcode connect-distributed.properties, so an
        override produced a unit pointing at a file that never exists and a
        service that cannot start.
        """
        work_dir = tempfile.mkdtemp()
        inv = os.path.join(work_dir, 'inventory')
        with open(inv, 'w') as f:
            f.write(INVENTORY)
        config_dir = os.path.join(work_dir, 'config')
        config_file = 'custom-connect.properties'

        try:
            r = ansible_runner.run(
                playbook='/app/tests/config_filename.yml',
                inventory=inv,
                extravars={
                    'redpanda_user': 'redpanda',
                    'redpanda_group': 'redpanda',
                    'redpanda_connect_config_dir': config_dir,
                    'connect_distributed_config_file': config_file,
                    # connect-distributed template inputs
                    'advertise_public_address': True,
                    'connect_tls_enabled': False,
                    'kafka_port': 9092,
                    'group_id': 'redpanda-kc',
                    'config_storage_topic': 'connect-configs',
                    'offset_storage_topic': 'connect-offsets',
                    'status_storage_topic': 'connect-status',
                    'key_converter': 'org.apache.kafka.connect.json.JsonConverter',
                    'value_converter': 'org.apache.kafka.connect.json.JsonConverter',
                    'rest_port': 8083,
                    'rest_advertised_port': 8083,
                    'rest_advertised_host_name': '127.0.0.1',
                    'plugin_path': '/opt/kafka/redpanda-plugins',
                    'plugin_discovery': 'hybrid_warn',
                    # unit template inputs
                    'redpanda_connect_home': '/opt/kafka',
                    'timeout_start_sec': 30,
                },
                quiet=False,
            )
            assert r.status == 'successful', f"Playbook failed: {r.rc}"

            written = os.path.join(config_dir, config_file)
            assert os.path.exists(written), \
                f"the config must land at the overridden name, missing: {written} " \
                f"(dir holds: {os.listdir(config_dir)})"

            with open(UNIT_PATH) as f:
                unit = f.read()
            assert f"ExecStart=/opt/kafka/bin/connect-distributed.sh {written}" in unit, \
                f"the unit's ExecStart must reference the written config, unit:\n{unit}"
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
            if os.path.exists(UNIT_PATH):
                os.unlink(UNIT_PATH)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))