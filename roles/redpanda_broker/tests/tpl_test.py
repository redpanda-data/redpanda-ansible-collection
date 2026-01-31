import pytest
import ansible_runner
import os


def run(playbook, templates, extra_vars=None):
    """Run a test playbook with the given templates and extra variables."""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    inv = os.path.join(test_dir, 'inventory')

    with open(inv, 'w') as f:
        f.write('localhost ansible_connection=local')

    vars_dict = {'test_templates': templates}
    if extra_vars:
        vars_dict.update(extra_vars)

    r = ansible_runner.run(
        playbook=os.path.join(test_dir, playbook),
        inventory=inv,
        extravars=vars_dict,
        quiet=False
    )

    # Extract configuration from the debug task output
    # The debug task outputs the variable directly in res['configuration']
    config = None
    for event in r.events:
        if event['event'] == 'runner_on_ok':
            event_data = event.get('event_data', {})
            res = event_data.get('res', {})
            task = event_data.get('task', '')

            # The debug task puts the variable directly in res
            if 'Debug' in task and 'configuration' in res:
                config = res['configuration']

    return r.status, config


class TestFixed:
    """Vars block approach - should pass."""

    def test_single(self):
        """Test single template with custom variables."""
        templates = [{"template": "templates/broker.json.j2"}]
        status, config = run('tpl_fixed.yml', templates, {'organization': 'my-org', 'kafka_ports': [9092, 9093]})
        assert status == 'successful'
        assert config['node']['organization'] == 'my-org'
        assert len(config['node']['redpanda']['kafka_api']) == 2

    def test_merge(self):
        """Test merging multiple templates (broker + TLS overlay)."""
        templates = [
            {"template": "templates/broker.json.j2"},
            {"template": "templates/tls.json.j2"}
        ]
        status, config = run('tpl_fixed.yml', templates)
        assert status == 'successful'
        assert config['node']['redpanda']['admin_api_tls']['enabled'] == True

    def test_deep(self):
        """Test deeply nested structure merging."""
        templates = [
            {"template": "templates/broker.json.j2"},
            {"template": "templates/deep.json.j2"}
        ]
        status, config = run('tpl_fixed.yml', templates)
        assert status == 'successful'
        assert config['level1']['level2']['level3']['level4']['deep_value'] == 'found'

    def test_whitespace(self):
        """Test template with leading/trailing whitespace."""
        templates = [{"template": "templates/whitespace.json.j2"}]
        status, config = run('tpl_fixed.yml', templates)
        assert status == 'successful'
        assert config['key'] == 'value_with_whitespace'

    def test_empty(self):
        """Test merging with empty template doesn't break existing config."""
        templates = [
            {"template": "templates/broker.json.j2"},
            {"template": "templates/empty.json.j2"}
        ]
        status, config = run('tpl_fixed.yml', templates)
        assert status == 'successful'
        assert 'cluster' in config

    def test_skip(self):
        """Test conditional skipping of templates."""
        templates = [
            {"template": "templates/broker.json.j2"},
            {"template": "templates/tls.json.j2", "condition": False}
        ]
        status, config = run('tpl_fixed.yml', templates)
        assert status == 'successful'
        assert 'admin_api_tls' not in config.get('node', {}).get('redpanda', {})


class TestBroken:
    """Multiline >- approach - should fail."""

    def test_fails(self):
        """The broken approach using >- should fail with type error on second iteration.

        The bug manifests when combining the result of iteration 1 (a string due to >-)
        with the dict from iteration 2. First iteration succeeds because {} | combine(dict)
        works, but second iteration fails because string | combine(dict) fails.
        """
        templates = [
            {"template": "templates/broker.json.j2"},
            {"template": "templates/tls.json.j2"}
        ]
        status, config = run('tpl_broken.yml', templates)
        assert status == 'failed', "Broken approach should fail when combining two templates"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
