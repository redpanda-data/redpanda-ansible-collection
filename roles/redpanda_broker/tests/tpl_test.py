import pytest
import ansible_runner
import os


# Only run the config generation tasks — skip everything that needs a real cluster
SKIP_TAGS = ','.join([
    'broker_ensure_dir',
    'broker_advertised_ip',
    'broker_check_initialized',
    'broker_set_initialized',
    'broker_write_config_first',
    'broker_write_bootstrap',
    'broker_bootstrap_superuser',
    'broker_start_tuner',
    'broker_start_sasl',
    'broker_start_standard',
    'broker_node_id',
    'broker_set_node_id',
    'broker_config_version',
    'broker_set_cluster_config',
    'broker_check_license_file',
    'broker_read_license',
    'broker_copy_license',
    'broker_check_license_status',
    'broker_license_needed',
    'broker_apply_license',
    'broker_remove_license',
    'broker_set_license_string',
    'broker_set_license_path',
    'broker_check_restart',
    'broker_check_restart_noauth',
    'broker_write_config_post',
    'broker_restart_required',
    'broker_safe_restart',
])

INVENTORY = """\
[redpanda]
node1 ansible_connection=local private_ip=10.0.0.1 advertised_ip=10.0.0.1
node2 ansible_connection=local private_ip=10.0.0.2 advertised_ip=10.0.0.2
node3 ansible_connection=local private_ip=10.0.0.3 advertised_ip=10.0.0.3
"""


def run(templates, extra_vars=None):
    inv = '/app/tests/inventory'
    with open(inv, 'w') as f:
        f.write(INVENTORY)

    vars_dict = {'test_templates': templates}
    if extra_vars:
        vars_dict.update(extra_vars)

    r = ansible_runner.run(
        playbook='/app/tests/tpl_test.yml',
        inventory=inv,
        extravars=vars_dict,
        cmdline=f'--skip-tags {SKIP_TAGS}',
        quiet=False
    )

    config = None
    for event in r.events:
        if event['event'] == 'runner_on_ok':
            event_data = event.get('event_data', {})
            res = event_data.get('res', {})
            task = event_data.get('task', '')
            if 'debug' in task.lower() and 'configuration' in res:
                config = res['configuration']

    return r.status, config


class TestBrokerTemplates:

    def test_defaults(self):
        templates = [{"template": "/app/templates/configs/defaults.j2"}]
        status, config = run(templates)
        assert status == 'successful'
        assert config['node']['organization'] == 'test-org'
        assert config['node']['redpanda']['data_directory'] == '/var/lib/redpanda/data'
        assert len(config['node']['redpanda']['seed_servers']) == 3
        assert len(config['node']['redpanda']['kafka_api']) == 1

    def test_defaults_tls_merge(self):
        templates = [
            {"template": "/app/templates/configs/defaults.j2"},
            {"template": "/app/templates/configs/tls.j2"}
        ]
        status, config = run(templates, {'enable_tls': True})
        assert status == 'successful'
        assert config['node']['redpanda']['admin_api_tls']['enabled'] == True
        assert len(config['node']['redpanda']['kafka_api_tls']) >= 1
        assert config['node']['redpanda']['rpc_server_tls']['enabled'] == True
        assert 'organization' in config['node']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
