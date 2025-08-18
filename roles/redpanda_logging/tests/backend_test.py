import unittest
import os
import yaml
from jinja2 import Environment, FileSystemLoader


class TestRedpandaLoggingBackend(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(self.current_dir, '..', 'templates')
        self.defaults_file = os.path.join(self.current_dir, '..', 'defaults', 'main.yml')
        
        # Load defaults
        with open(self.defaults_file, 'r') as f:
            self.defaults = yaml.safe_load(f)
        
        # Create Jinja2 environment
        self.env = Environment(loader=FileSystemLoader(self.templates_dir))
    
    def test_defaults_backend_selection(self):
        """Test that default backend is rsyslog."""
        self.assertEqual(self.defaults['redpanda_logging_backend'], 'rsyslog')
        self.assertIn('redpanda_logging_rsyslog_priority', self.defaults)
        self.assertIn('redpanda_logging_syslog_ng_priority', self.defaults)
    
    def test_logrotate_postrotate_rsyslog(self):
        """Test logrotate postrotate command for rsyslog backend."""
        template = self.env.get_template('redpanda-logrotate.conf.j2')
        
        context = {
            'redpanda_logging_backend': 'rsyslog',
            'redpanda_logging_log_file': '/var/log/redpanda.log',
            'redpanda_logging_logrotate_frequency': 'daily',
            'redpanda_logging_logrotate_rotate': 7,
            'redpanda_logging_logrotate_maxsize': '100M',
            'redpanda_logging_logrotate_compress': True,
            'redpanda_logging_logrotate_delaycompress': True,
            'redpanda_logging_logrotate_notifempty': True,
            'redpanda_logging_logrotate_create': True,
            'redpanda_logging_logrotate_sharedscripts': True,
            'redpanda_logging_file_mode': '0640',
            'redpanda_logging_owner': 'syslog',
            'redpanda_logging_group': 'adm',
            'redpanda_logging_logrotate_postrotate_command': self.defaults['redpanda_logging_logrotate_postrotate_rsyslog']
        }
        
        rendered_template = template.render(**context)
        
        # Verify rsyslog-specific postrotate commands
        self.assertIn('/var/run/rsyslogd.pid', rendered_template)
        self.assertIn('/run/rsyslogd.pid', rendered_template)
        self.assertNotIn('/var/run/syslog-ng.pid', rendered_template)
        self.assertNotIn('/run/syslog-ng.pid', rendered_template)
    
    def test_logrotate_postrotate_syslog_ng(self):
        """Test logrotate postrotate command for syslog-ng backend."""
        template = self.env.get_template('redpanda-logrotate.conf.j2')
        
        context = {
            'redpanda_logging_backend': 'syslog-ng',
            'redpanda_logging_log_file': '/var/log/redpanda.log',
            'redpanda_logging_logrotate_frequency': 'daily',
            'redpanda_logging_logrotate_rotate': 7,
            'redpanda_logging_logrotate_maxsize': '100M',
            'redpanda_logging_logrotate_compress': True,
            'redpanda_logging_logrotate_delaycompress': True,
            'redpanda_logging_logrotate_notifempty': True,
            'redpanda_logging_logrotate_create': True,
            'redpanda_logging_logrotate_sharedscripts': True,
            'redpanda_logging_file_mode': '0640',
            'redpanda_logging_owner': 'syslog',
            'redpanda_logging_group': 'adm',
            'redpanda_logging_logrotate_postrotate_command': self.defaults['redpanda_logging_logrotate_postrotate_syslog_ng']
        }
        
        rendered_template = template.render(**context)
        
        # Verify syslog-ng-specific postrotate commands
        self.assertIn('/var/run/syslog-ng.pid', rendered_template)
        self.assertIn('/run/syslog-ng.pid', rendered_template)
        self.assertNotIn('/var/run/rsyslogd.pid', rendered_template)
        self.assertNotIn('/run/rsyslogd.pid', rendered_template)
    
    def test_backend_validation(self):
        """Test that backend validation works correctly."""
        valid_backends = ['rsyslog', 'syslog-ng']
        
        # Test that default backend is valid
        self.assertIn(self.defaults['redpanda_logging_backend'], valid_backends)
        
        # Test expected backend configurations
        for backend in valid_backends:
            # Each backend should have a priority setting
            priority_key = f'redpanda_logging_{backend.replace("-", "_")}_priority'
            self.assertIn(priority_key, self.defaults)
    
    def test_shared_variables_exist(self):
        """Test that all shared variables exist in defaults."""
        shared_variables = [
            'redpanda_logging_enabled',
            'redpanda_logging_log_file',
            'redpanda_logging_owner',
            'redpanda_logging_group',
            'redpanda_logging_dir_mode',
            'redpanda_logging_file_mode',
            'redpanda_logging_logrotate_enabled',
            'redpanda_logging_logrotate_frequency',
            'redpanda_logging_logrotate_rotate',
            'redpanda_logging_logrotate_maxsize',
            'redpanda_logging_logrotate_compress',
            'redpanda_logging_logrotate_delaycompress',
            'redpanda_logging_logrotate_notifempty'
        ]
        
        for var in shared_variables:
            self.assertIn(var, self.defaults, f"Missing shared variable: {var}")
    
    def test_backend_specific_variables_exist(self):
        """Test that backend-specific variables exist."""
        backend_variables = [
            'redpanda_logging_backend',
            'redpanda_logging_rsyslog_priority',
            'redpanda_logging_syslog_ng_priority',
        ]
        
        for var in backend_variables:
            self.assertIn(var, self.defaults, f"Missing backend variable: {var}")
    
    def test_installation_logic_in_tasks(self):
        """Test that installation checks are present in main tasks."""
        import os
        tasks_file = os.path.join(self.current_dir, '..', 'tasks', 'main.yml')
        
        with open(tasks_file, 'r') as f:
            tasks_content = f.read()
        
        # Check for installation logic
        self.assertIn('Check if rsyslog is installed', tasks_content)
        self.assertIn('Install rsyslog package', tasks_content)
        self.assertIn('Check if syslog-ng is installed', tasks_content)
        self.assertIn('Install syslog-ng package', tasks_content)
        self.assertIn('systemctl list-unit-files', tasks_content)
        self.assertIn('ansible.builtin.package:', tasks_content)
    
    def test_conditional_installation_logic(self):
        """Test that installation is conditional on backend selection."""
        import os
        tasks_file = os.path.join(self.current_dir, '..', 'tasks', 'main.yml')
        
        with open(tasks_file, 'r') as f:
            tasks_content = f.read()
        
        # Check that installation tasks are within backend-specific blocks
        rsyslog_block_start = tasks_content.find('when: redpanda_logging_backend == \'rsyslog\'')
        syslog_ng_block_start = tasks_content.find('when: redpanda_logging_backend == \'syslog-ng\'')
        
        self.assertNotEqual(rsyslog_block_start, -1, "rsyslog backend block not found")
        self.assertNotEqual(syslog_ng_block_start, -1, "syslog-ng backend block not found")
        
        # Check that install tasks are within the correct blocks
        install_rsyslog_pos = tasks_content.find('Install rsyslog package')
        install_syslog_ng_pos = tasks_content.find('Install syslog-ng package')
        
        self.assertTrue(install_rsyslog_pos > rsyslog_block_start, 
                       "rsyslog installation should be within rsyslog block")
        self.assertTrue(install_syslog_ng_pos > syslog_ng_block_start,
                       "syslog-ng installation should be within syslog-ng block")
    
    def test_rsyslog_template_exists(self):
        """Test that rsyslog template can be loaded."""
        template = self.env.get_template('redpanda-rsyslog.conf.j2')
        self.assertIsNotNone(template)
    
    def test_syslog_ng_template_exists(self):
        """Test that syslog-ng template can be loaded."""
        template = self.env.get_template('redpanda-syslog-ng.conf.j2')
        self.assertIsNotNone(template)
    
    def test_logrotate_template_exists(self):
        """Test that logrotate template can be loaded."""
        template = self.env.get_template('redpanda-logrotate.conf.j2')
        self.assertIsNotNone(template)


if __name__ == '__main__':
    unittest.main()