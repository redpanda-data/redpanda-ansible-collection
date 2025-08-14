import unittest
import os
import yaml
from jinja2 import Environment, FileSystemLoader


class TestRedpandaSyslogNgTemplate(unittest.TestCase):
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
    
    def test_syslog_ng_default_config(self):
        """Test syslog-ng config with default values."""
        template = self.env.get_template('redpanda-syslog-ng.conf.j2')
        
        # Test data with default values
        context = {
            'redpanda_logging_log_file': '/var/log/redpanda.log',
            'redpanda_logging_program': 'rpk',
            'redpanda_logging_syslog_ng_source': 's_src'
        }
        
        rendered_template = template.render(**context)
        
        # Verify default configuration
        self.assertIn('filter f_redpanda { program("rpk"); };', rendered_template)
        self.assertIn('destination d_redpanda { file("/var/log/redpanda.log"); };', rendered_template)
        self.assertIn('log { source(s_src); filter(f_redpanda); destination(d_redpanda); flags(final); };', rendered_template)
    
    def test_syslog_ng_custom_path(self):
        """Test syslog-ng config with custom log path."""
        template = self.env.get_template('redpanda-syslog-ng.conf.j2')
        
        # Test data with custom path
        context = {
            'redpanda_logging_log_file': '/app/logs/redpanda.log',
            'redpanda_logging_program': 'rpk',
            'redpanda_logging_syslog_ng_source': 's_src'
        }
        
        rendered_template = template.render(**context)
        
        # Verify custom path is used
        self.assertIn('filter f_redpanda { program("rpk"); };', rendered_template)
        self.assertIn('destination d_redpanda { file("/app/logs/redpanda.log"); };', rendered_template)
    
    def test_syslog_ng_custom_program_name(self):
        """Test syslog-ng config with custom program name."""
        template = self.env.get_template('redpanda-syslog-ng.conf.j2')
        
        # Test data with custom program name
        context = {
            'redpanda_logging_log_file': '/var/log/redpanda.log',
            'redpanda_logging_program': 'redpanda-broker',
            'redpanda_logging_syslog_ng_source': 's_src'
        }
        
        rendered_template = template.render(**context)
        
        # Verify custom program name is used
        self.assertIn('filter f_redpanda { program("redpanda-broker"); };', rendered_template)
        self.assertIn('destination d_redpanda { file("/var/log/redpanda.log"); };', rendered_template)


if __name__ == '__main__':
    unittest.main()