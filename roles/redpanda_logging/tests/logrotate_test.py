import unittest
import os
import yaml
from jinja2 import Environment, FileSystemLoader


class TestRedpandaLogrotateTemplate(unittest.TestCase):
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
    
    def test_logrotate_default_config_debian(self):
        """Test logrotate config with default values for Debian/Ubuntu."""
        template = self.env.get_template('redpanda-logrotate.conf.j2')
        
        # Simulate Debian/Ubuntu environment
        context = {
            'redpanda_logging_log_file': self.defaults['redpanda_logging_log_file'],
            'redpanda_logging_logrotate_frequency': self.defaults['redpanda_logging_logrotate_frequency'],
            'redpanda_logging_logrotate_rotate': self.defaults['redpanda_logging_logrotate_rotate'],
            'redpanda_logging_logrotate_maxsize': self.defaults['redpanda_logging_logrotate_maxsize'],
            'redpanda_logging_logrotate_compress': self.defaults['redpanda_logging_logrotate_compress'],
            'redpanda_logging_logrotate_delaycompress': self.defaults['redpanda_logging_logrotate_delaycompress'],
            'redpanda_logging_logrotate_notifempty': self.defaults['redpanda_logging_logrotate_notifempty'],
            'redpanda_logging_logrotate_create': self.defaults['redpanda_logging_logrotate_create'],
            'redpanda_logging_logrotate_sharedscripts': self.defaults['redpanda_logging_logrotate_sharedscripts'],
            'redpanda_logging_file_mode': self.defaults['redpanda_logging_file_mode'],
            'redpanda_logging_owner': 'syslog',  # Debian default
            'redpanda_logging_group': 'adm',     # Debian default
            'redpanda_logging_logrotate_postrotate_command': self.defaults['redpanda_logging_logrotate_postrotate_command'],
            'ansible_os_family': 'Debian'  # Mock OS family
        }
        
        rendered_template = template.render(**context)
        
        # Verify default settings for Debian
        self.assertIn('/var/log/redpanda.log', rendered_template)
        self.assertIn('daily', rendered_template)
        self.assertIn('rotate 7', rendered_template)
        self.assertIn('maxsize 100M', rendered_template)
        self.assertIn('su syslog adm', rendered_template)
        self.assertIn('compress', rendered_template)
        self.assertIn('delaycompress', rendered_template)
        self.assertIn('notifempty', rendered_template)
        self.assertIn('create 0640 syslog adm', rendered_template)
        self.assertIn('sharedscripts', rendered_template)
        self.assertIn('postrotate', rendered_template)
        self.assertIn('for pidfile in', rendered_template)
        
    def test_logrotate_default_config_redhat(self):
        """Test logrotate config with default values for RedHat/Fedora."""
        template = self.env.get_template('redpanda-logrotate.conf.j2')
        
        # Simulate RedHat/Fedora environment
        context = {
            'redpanda_logging_log_file': self.defaults['redpanda_logging_log_file'],
            'redpanda_logging_logrotate_frequency': self.defaults['redpanda_logging_logrotate_frequency'],
            'redpanda_logging_logrotate_rotate': self.defaults['redpanda_logging_logrotate_rotate'],
            'redpanda_logging_logrotate_maxsize': self.defaults['redpanda_logging_logrotate_maxsize'],
            'redpanda_logging_logrotate_compress': self.defaults['redpanda_logging_logrotate_compress'],
            'redpanda_logging_logrotate_delaycompress': self.defaults['redpanda_logging_logrotate_delaycompress'],
            'redpanda_logging_logrotate_notifempty': self.defaults['redpanda_logging_logrotate_notifempty'],
            'redpanda_logging_logrotate_create': self.defaults['redpanda_logging_logrotate_create'],
            'redpanda_logging_logrotate_sharedscripts': self.defaults['redpanda_logging_logrotate_sharedscripts'],
            'redpanda_logging_file_mode': self.defaults['redpanda_logging_file_mode'],
            'redpanda_logging_owner': 'root',    # RedHat default
            'redpanda_logging_group': 'root',    # RedHat default
            'redpanda_logging_logrotate_postrotate_command': self.defaults['redpanda_logging_logrotate_postrotate_command'],
            'ansible_os_family': 'RedHat'  # Mock OS family
        }
        
        rendered_template = template.render(**context)
        
        # Verify default settings for RedHat
        self.assertIn('/var/log/redpanda.log', rendered_template)
        self.assertIn('daily', rendered_template)
        self.assertIn('rotate 7', rendered_template)
        self.assertIn('maxsize 100M', rendered_template)
        self.assertIn('su root root', rendered_template)
        self.assertIn('compress', rendered_template)
        self.assertIn('delaycompress', rendered_template)
        self.assertIn('notifempty', rendered_template)
        self.assertIn('create 0640 root root', rendered_template)
        self.assertIn('sharedscripts', rendered_template)
        self.assertIn('postrotate', rendered_template)
        self.assertIn('for pidfile in', rendered_template)
    
    def test_logrotate_custom_rotation(self):
        """Test logrotate config with custom rotation settings."""
        template = self.env.get_template('redpanda-logrotate.conf.j2')
        
        context = {
            'redpanda_logging_log_file': '/app/logs/redpanda.log',
            'redpanda_logging_logrotate_frequency': 'weekly',
            'redpanda_logging_logrotate_rotate': 30,
            'redpanda_logging_logrotate_maxsize': '500M',
            'redpanda_logging_logrotate_compress': True,
            'redpanda_logging_logrotate_delaycompress': True,
            'redpanda_logging_logrotate_notifempty': True,
            'redpanda_logging_logrotate_create': True,
            'redpanda_logging_logrotate_sharedscripts': True,
            'redpanda_logging_file_mode': '0644',
            'redpanda_logging_owner': 'redpanda',
            'redpanda_logging_group': 'redpanda',
            'redpanda_logging_logrotate_postrotate_command': 'systemctl reload rsyslog'
        }
        
        rendered_template = template.render(**context)
        
        # Verify custom settings
        self.assertIn('/app/logs/redpanda.log', rendered_template)
        self.assertIn('weekly', rendered_template)
        self.assertIn('rotate 30', rendered_template)
        self.assertIn('maxsize 500M', rendered_template)
        self.assertIn('su redpanda redpanda', rendered_template)
        self.assertIn('create 0644 redpanda redpanda', rendered_template)
        self.assertIn('systemctl reload rsyslog', rendered_template)
    
    def test_logrotate_no_compression(self):
        """Test logrotate config without compression."""
        template = self.env.get_template('redpanda-logrotate.conf.j2')
        
        context = {
            'redpanda_logging_log_file': '/var/log/redpanda.log',
            'redpanda_logging_logrotate_frequency': 'daily',
            'redpanda_logging_logrotate_rotate': 7,
            'redpanda_logging_logrotate_maxsize': '100M',
            'redpanda_logging_logrotate_compress': False,
            'redpanda_logging_logrotate_delaycompress': False,
            'redpanda_logging_logrotate_notifempty': True,
            'redpanda_logging_logrotate_create': True,
            'redpanda_logging_logrotate_sharedscripts': True,
            'redpanda_logging_file_mode': '0640',
            'redpanda_logging_owner': 'syslog',
            'redpanda_logging_group': 'adm',
            'redpanda_logging_logrotate_postrotate_command': 'true'
        }
        
        rendered_template = template.render(**context)
        
        # Verify compression is not present
        self.assertNotIn('compress', rendered_template)
        self.assertNotIn('delaycompress', rendered_template)
        # Verify su directive is present
        self.assertIn('su syslog adm', rendered_template)
    
    def test_logrotate_no_create(self):
        """Test logrotate config without create directive."""
        template = self.env.get_template('redpanda-logrotate.conf.j2')
        
        context = {
            'redpanda_logging_log_file': '/var/log/redpanda.log',
            'redpanda_logging_logrotate_frequency': 'daily',
            'redpanda_logging_logrotate_rotate': 7,
            'redpanda_logging_logrotate_maxsize': '100M',
            'redpanda_logging_logrotate_compress': True,
            'redpanda_logging_logrotate_delaycompress': True,
            'redpanda_logging_logrotate_notifempty': True,
            'redpanda_logging_logrotate_create': False,
            'redpanda_logging_logrotate_sharedscripts': False,
            'redpanda_logging_file_mode': '0640',
            'redpanda_logging_owner': 'syslog',
            'redpanda_logging_group': 'adm',
            'redpanda_logging_logrotate_postrotate_command': 'true'
        }
        
        rendered_template = template.render(**context)
        
        # Verify create is not present
        self.assertNotIn('create', rendered_template)
        self.assertNotIn('sharedscripts', rendered_template)
        # Verify su directive is present
        self.assertIn('su syslog adm', rendered_template)
    
    def test_logrotate_multiline_postrotate(self):
        """Test logrotate config with multiline postrotate command."""
        template = self.env.get_template('redpanda-logrotate.conf.j2')
        
        multiline_command = """if [ -f /var/run/rsyslogd.pid ]; then
    /bin/kill -HUP `cat /var/run/rsyslogd.pid`
fi"""
        
        context = {
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
            'redpanda_logging_logrotate_postrotate_command': multiline_command
        }
        
        rendered_template = template.render(**context)
        
        # Verify multiline command is properly indented
        self.assertIn('postrotate', rendered_template)
        self.assertIn('        if [ -f /var/run/rsyslogd.pid ]; then', rendered_template)
        self.assertIn('            /bin/kill -HUP', rendered_template)
        self.assertIn('        fi', rendered_template)
        self.assertIn('endscript', rendered_template)
        # Verify su directive is present
        self.assertIn('su syslog adm', rendered_template)


if __name__ == '__main__':
    unittest.main()