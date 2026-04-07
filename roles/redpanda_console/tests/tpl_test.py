import pytest
import ansible_runner
import os


SKIP_TAGS = 'console_ensure_dir,console_advertised_ips,console_connect_ips,console_write_config'


def run(templates, extra_vars=None):
    inv = '/app/tests/inventory'
    with open(inv, 'w') as f:
        f.write('localhost ansible_connection=local')

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
            if 'debug' in task.lower() and 'console_config' in res:
                config = res['console_config']

    return r.status, config


class TestConsoleTemplates:

    def test_defaults(self):
        templates = [{"template": "/app/templates/defaults.j2"}]
        status, config = run(templates)
        assert status == 'successful'
        assert len(config['kafka']['brokers']) == 3
        assert config['kafka']['brokers'][0] == '10.0.0.1:9092'
        assert config['schemaRegistry']['enabled'] == True
        assert len(config['schemaRegistry']['urls']) == 3
        assert config['redpanda']['adminApi']['enabled'] == True

    def test_defaults_with_tls(self):
        templates = [{"template": "/app/templates/defaults.j2"}]
        status, config = run(templates, {'enable_tls': True})
        assert status == 'successful'
        assert config['kafka']['tls']['enabled'] == True
        assert config['redpanda']['adminApi']['tls']['enabled'] == True
        assert config['server']['tls']['enabled'] == True
        assert 'https' in config['schemaRegistry']['urls'][0]

    def test_pre_v3(self):
        templates = [{"template": "/app/templates/pre_v3_defaults.j2"}]
        status, config = run(templates)
        assert status == 'successful'
        assert len(config['kafka']['brokers']) == 3
        assert config['kafka']['schemaRegistry']['enabled'] == True
        assert config['redpanda']['adminApi']['enabled'] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
