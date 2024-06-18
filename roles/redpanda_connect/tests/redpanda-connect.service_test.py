import unittest
import os
import yaml
from jinja2 import Environment, FileSystemLoader

class TestRedpandaConnectService(unittest.TestCase):
    def test_connect_service_template(self):
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
        template = env.get_template('redpanda-connect.service.j2')

        # Define the hostvars and groups for rendering the template
        hostvars = {
            '10.9.8.7': {
                'ansible_host': '10.9.8.7',
                'private_ip': '1.2.3.4',
            },
            '10.9.8.6': {
                'ansible_host': '10.9.8.7',
                'private_ip': '1.2.3.4',
            },
            '10.9.8.5': {
                'ansible_host': '10.9.8.7',
                'private_ip': '1.2.3.4',
            },
        }
        groups = {
            'connect': ['10.9.8.7', '10.9.8.6', '10.9.8.5']
        }
        inventory_hostname = '10.9.8.7'

        # Render the template with the provided hostvars, groups, and defaults
        rendered_template = template.render(hostvars=hostvars, groups=groups, inventory_hostname=inventory_hostname, **defaults)

        # Define the expected values
        expected_user = f"User=redpanda"
        expected_group = f"Group=redpanda"
        expected_plugin_path = f"Environment=\"CONNECT_PLUGIN_PATH=/opt/kafka/plugins\""
        expected_exec_start = f"ExecStart=/opt/kafka/bin/connect-distributed.sh /opt/kafka/config/connect-distributed.properties"
        expected_kafka_opts = f"Environment=\"KAFKA_OPTS= -javaagent:/opt/kafka/redpanda-plugins/jmx-exporter/jmx_prometheus_javaagent.jar=9404:/opt/kafka/config/jmx-exporter-config.json\""

        # Assert the presence of expected lines in the rendered template
        self.assertIn(expected_user, rendered_template)
        self.assertIn(expected_group, rendered_template)
        self.assertIn(expected_plugin_path, rendered_template)
        self.assertIn(expected_exec_start, rendered_template)

        # Assert the presence of optional KAFKA_OPTS environment variable if defined
        if 'KAFKA_OPTS' in defaults and defaults['KAFKA_OPTS'] != "":
            self.assertIn(f"Environment=\"KAFKA_OPTS={defaults['KAFKA_OPTS']}\"", rendered_template)

        print(rendered_template)

if __name__ == '__main__':
    unittest.main()
