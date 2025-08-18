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
    
    def test_syslog_ng_default_config_debian(self):
        """Test syslog-ng config with default values for Debian/Ubuntu."""
        template = self.env.get_template('redpanda-syslog-ng.conf.j2')
        
        # Simulate Debian/Ubuntu environment
        context = {
            'redpanda_logging_log_file': self.defaults['redpanda_logging_log_file'],
            'redpanda_logging_program': self.defaults['redpanda_logging_program'],
            'redpanda_logging_owner': 'syslog',  # Debian default
            'redpanda_logging_group': 'adm',     # Debian default
            'redpanda_logging_file_mode': self.defaults['redpanda_logging_file_mode'],
            'redpanda_logging_dir_mode': self.defaults['redpanda_logging_dir_mode'],
            'ansible_os_family': 'Debian'  # Mock OS family
        }
        
        rendered_template = template.render(**context)
        
        # Verify default settings for Debian
        self.assertIn('filter f_redpanda { program("rpk"); };', rendered_template)
        self.assertIn('file("/var/log/redpanda.log"', rendered_template)
        self.assertIn('owner("syslog")', rendered_template)
        self.assertIn('group("adm")', rendered_template)
        self.assertIn('perm(0640)', rendered_template)
        self.assertIn('dir-perm(0755)', rendered_template)
        self.assertIn('create-dirs(yes)', rendered_template)
        self.assertIn('source(s_src);', rendered_template)
        self.assertIn('filter(f_redpanda);', rendered_template)
        self.assertIn('destination(d_redpanda);', rendered_template)
        self.assertIn('flags(final);', rendered_template)
    
    def test_syslog_ng_default_config_redhat(self):
        """Test syslog-ng config with default values for RedHat/Fedora."""
        template = self.env.get_template('redpanda-syslog-ng.conf.j2')
        
        # Simulate RedHat/Fedora environment
        context = {
            'redpanda_logging_log_file': self.defaults['redpanda_logging_log_file'],
            'redpanda_logging_program': self.defaults['redpanda_logging_program'],
            'redpanda_logging_owner': 'root',    # RedHat default
            'redpanda_logging_group': 'root',    # RedHat default
            'redpanda_logging_file_mode': self.defaults['redpanda_logging_file_mode'],
            'redpanda_logging_dir_mode': self.defaults['redpanda_logging_dir_mode'],
            'ansible_os_family': 'RedHat'  # Mock OS family
        }
        
        rendered_template = template.render(**context)
        
        # Verify default settings for RedHat
        self.assertIn('filter f_redpanda { program("rpk"); };', rendered_template)
        self.assertIn('file("/var/log/redpanda.log"', rendered_template)
        self.assertIn('owner("root")', rendered_template)
        self.assertIn('group("root")', rendered_template)
        self.assertIn('perm(0640)', rendered_template)
        self.assertIn('dir-perm(0755)', rendered_template)
        self.assertIn('create-dirs(yes)', rendered_template)
        self.assertIn('source(s_src);', rendered_template)
        self.assertIn('filter(f_redpanda);', rendered_template)
        self.assertIn('destination(d_redpanda);', rendered_template)
        self.assertIn('flags(final);', rendered_template)
    
    def test_syslog_ng_custom_path(self):
        """Test syslog-ng config with custom log path."""
        template = self.env.get_template('redpanda-syslog-ng.conf.j2')
        
        context = {
            'redpanda_logging_log_file': '/app/logs/redpanda.log',
            'redpanda_logging_program': 'redpanda-broker',
            'redpanda_logging_owner': 'redpanda',
            'redpanda_logging_group': 'redpanda',
            'redpanda_logging_file_mode': '0644',
            'redpanda_logging_dir_mode': '0755'
        }
        
        rendered_template = template.render(**context)
        
        # Verify custom settings
        self.assertIn('filter f_redpanda { program("redpanda-broker"); };', rendered_template)
        self.assertIn('file("/app/logs/redpanda.log"', rendered_template)
        self.assertIn('owner("redpanda")', rendered_template)
        self.assertIn('group("redpanda")', rendered_template)
        self.assertIn('perm(0644)', rendered_template)
        self.assertIn('dir-perm(0755)', rendered_template)
    
    def test_syslog_ng_permission_conversion(self):
        """Test that octal permissions are correctly converted."""
        template = self.env.get_template('redpanda-syslog-ng.conf.j2')
        
        context = {
            'redpanda_logging_log_file': '/var/log/redpanda.log',
            'redpanda_logging_program': 'rpk',
            'redpanda_logging_owner': 'syslog',
            'redpanda_logging_group': 'adm',
            'redpanda_logging_file_mode': '0600',  # String format
            'redpanda_logging_dir_mode': '0750'    # String format
        }
        
        rendered_template = template.render(**context)
        
        # Verify octal conversion
        self.assertIn('perm(0600)', rendered_template)
        self.assertIn('dir-perm(0750)', rendered_template)
    
    def test_syslog_ng_structure(self):
        """Test that syslog-ng config has correct structure."""
        template = self.env.get_template('redpanda-syslog-ng.conf.j2')
        
        context = {
            'redpanda_logging_log_file': '/var/log/redpanda.log',
            'redpanda_logging_program': 'rpk',
            'redpanda_logging_owner': 'syslog',
            'redpanda_logging_group': 'adm',
            'redpanda_logging_file_mode': '0640',
            'redpanda_logging_dir_mode': '0755'
        }
        
        rendered_template = template.render(**context)
        
        # Verify structure elements are present in correct order
        filter_pos = rendered_template.find('filter f_redpanda')
        destination_pos = rendered_template.find('destination d_redpanda')
        log_pos = rendered_template.find('log {')
        
        # Filter should come first, then destination, then log block
        self.assertTrue(filter_pos < destination_pos < log_pos)
        
        # Verify log block contains required elements
        log_block_start = rendered_template.find('log {')
        log_block_end = rendered_template.find('};', log_block_start)
        log_block = rendered_template[log_block_start:log_block_end + 2]
        
        self.assertIn('source(s_src);', log_block)
        self.assertIn('filter(f_redpanda);', log_block)
        self.assertIn('destination(d_redpanda);', log_block)
        self.assertIn('flags(final);', log_block)


if __name__ == '__main__':
    unittest.main()