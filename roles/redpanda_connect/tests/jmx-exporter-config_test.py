import unittest
import os
import yaml
from jinja2 import Environment, FileSystemLoader

class TestJmxExporterConfig(unittest.TestCase):
    def test_bootstrap_server_template(self):
        # Get the absolute path of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Construct the path to the templates directory
        templates_dir = os.path.join(current_dir, '..', 'templates')

        # Construct the path to the defaults/main.yml file
        defaults_file = os.path.join(current_dir, '..', 'defaults', 'main.yml')

        # Load the defaults from the YAML file
        with open(defaults_file, 'r') as f:
            defaults = yaml.safe_load(f)

        # Create a Jinja2 environment and load the template from file
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template('jmx-exporter-config.json.j2')

        # Define the hostvars and groups for rendering the template
        hostvars = {
            '35.91.106.231': {
                'ansible_host': '35.91.106.231',
            },
            '35.88.129.205': {
                'ansible_host': '35.88.129.205',
            },
            '54.190.184.126': {
                'ansible_host': '54.190.184.126',
            }
        }
        advertised_ips = ["35.91.106.231", "35.88.129.205", "54.190.184.126"]
        groups = {
            'connect': ['35.91.106.231', '35.88.129.205', '54.190.184.126']
        }
        jmx_ssl = "true"

        # Render the template with the provided hostvars, groups, and defaults
        rendered_template = template.render(hostvars=hostvars, advertised_ips=advertised_ips, groups=groups, jmx_ssl=jmx_ssl, **defaults)

        # Define the expected bootstrap server line
        #expected_bootstrap_servers = 'bootstrap.servers=35.91.106.231:9092,35.88.129.205:9092,54.190.184.126:9092'

        # Assert that the expected line is contained within the rendered template
        #self.assertIn(expected_bootstrap_servers, rendered_template)


        print(rendered_template)

if __name__ == '__main__':
    unittest.main()
