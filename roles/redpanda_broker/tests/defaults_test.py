import unittest
import os
import yaml
from jinja2 import Environment, FileSystemLoader

class TestRedpandaTemplate(unittest.TestCase):
    def setUp(self):
        # Get the absolute path of the current file
        self.current_dir = os.path.dirname(os.path.abspath(__file__))

        # Construct the path to the templates directory
        self.templates_dir = os.path.join(self.current_dir, '..', 'templates/configs')

        # Construct the path to the defaults/main.yml file
        self.defaults_file = os.path.join(self.current_dir, '..', 'defaults', 'main.yml')

        # Load the defaults from the YAML file
        with open(self.defaults_file, 'r') as f:
            self.defaults = yaml.safe_load(f)

        # Create a Jinja2 environment
        self.env = Environment(loader=FileSystemLoader(self.templates_dir))

        # Define the hostvars and groups for rendering the template
        self.hostvars = {
            '35.91.106.231': {
                'ansible_host': '35.91.106.231',
                'advertised_ip': '35.91.106.231',
                'private_ip': '192.168.1.1'
            },
            '35.88.129.205': {
                'ansible_host': '35.88.129.205',
                'advertised_ip': '35.88.129.205',
                'private_ip': '192.168.1.2'
            },
            '54.190.184.126': {
                'ansible_host': '54.190.184.126',
                'advertised_ip': '54.190.184.126',
                'private_ip': '192.168.1.3'
            }
        }
        self.groups = {
            'redpanda': ['35.91.106.231', '35.88.129.205', '54.190.184.126']
        }

    def test_redpanda_template_default_listener(self):
        # Load the template from file
        template = self.env.get_template('defaults.j2')

        # Render the template with the provided hostvars, groups, and defaults without multiple_advertised_kafka_listeners
        rendered_template = template.render(
            hostvars=self.hostvars,
            groups=self.groups,
            inventory_hostname='35.91.106.231',
            **self.defaults
        )

        # Define the expected default advertised_kafka_api value
        expected_advertised_kafka_api_default = {
            "address": "35.91.106.231",
            "port": str(self.defaults['redpanda_kafka_port'])
        }

        # Convert the rendered template to a dictionary for easier comparison
        rendered_dict = yaml.safe_load(rendered_template)

        # Assert that the expected default value is in the rendered template
        self.assertIn(expected_advertised_kafka_api_default, rendered_dict['node']['redpanda']['advertised_kafka_api'])

        print(rendered_template)

if __name__ == '__main__':
    unittest.main()
