import unittest
import os
import yaml
from jinja2 import Environment, FileSystemLoader
import json


class TestDefaultsTemplate(unittest.TestCase):
    def test_defaults_template(self):
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
        template = env.get_template('defaults.j2')

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
            'redpanda': ['35.91.106.231', '35.88.129.205', '54.190.184.126']
        }

        # Set up some test cases for enable_tls
        scenarios = [
            {'enable_tls': False, 'name': 'without TLS'},
            {'enable_tls': True, 'name': 'with TLS'}
        ]

        for scenario in scenarios:
            # Merge scenario settings with defaults
            test_vars = {**defaults, **scenario}

            # Render the template
            rendered_template = template.render(
                hostvars=hostvars,
                advertised_ips=advertised_ips,
                groups=groups,
                **test_vars
            )

            # Parse the rendered JSON to validate its structure
            try:
                parsed_json = json.loads(rendered_template)

                # Test that expected sections exist in the JSON
                self.assertIn("kafka", parsed_json)
                self.assertIn("brokers", parsed_json["kafka"])
                self.assertIn("redpanda", parsed_json)
                self.assertIn("adminApi", parsed_json["redpanda"])
                self.assertIn("schemaRegistry", parsed_json)

                # Test that TLS settings are present when enable_tls is True
                if scenario['enable_tls']:
                    self.assertIn("tls", parsed_json["kafka"])
                    self.assertTrue(parsed_json["kafka"]["tls"]["enabled"])
                    self.assertIn("tls", parsed_json["redpanda"]["adminApi"])
                    self.assertTrue(parsed_json["redpanda"]["adminApi"]["tls"]["enabled"])
                    self.assertIn("server", parsed_json)
                    self.assertIn("tls", parsed_json["server"])
                    self.assertTrue(parsed_json["server"]["tls"]["enabled"])
                else:
                    self.assertNotIn("tls", parsed_json.get("kafka", {}))

                # Test kafka brokers
                self.assertEqual(len(parsed_json["kafka"]["brokers"]), 3)
                for i, ip in enumerate(advertised_ips):
                    expected_broker = f"{ip}:{defaults['redpanda_kafka_port']}"
                    self.assertEqual(parsed_json["kafka"]["brokers"][i], expected_broker)

                # Test admin API URLs
                admin_urls = parsed_json["redpanda"]["adminApi"]["urls"]
                self.assertEqual(len(admin_urls), 3)
                protocol = "https" if scenario['enable_tls'] else "http"
                for i, ip in enumerate(advertised_ips):
                    expected_url = f"{protocol}://{ip}:{defaults['redpanda_admin_api_port']}"
                    self.assertEqual(admin_urls[i], expected_url)

                # Test schema registry URLs
                schema_urls = parsed_json["schemaRegistry"]["urls"]
                self.assertEqual(len(schema_urls), 3)
                for i, ip in enumerate(advertised_ips):
                    expected_url = f"{protocol}://{ip}:{defaults['redpanda_schema_registry_port']}"
                    self.assertEqual(schema_urls[i], expected_url)

                # Test kafkaConnect settings if applicable
                if "connect" in groups:
                    self.assertIn("kafkaConnect", parsed_json)
                    self.assertTrue(parsed_json["kafkaConnect"]["enabled"])
                    self.assertEqual(len(parsed_json["kafkaConnect"]["clusters"]), 1)
                    self.assertEqual(parsed_json["kafkaConnect"]["clusters"][0]["name"], "Connect")

                print(f"Successfully validated scenario: {scenario['name']}")

            except json.JSONDecodeError as e:
                self.fail(f"Failed to parse rendered JSON template: {e}")
                print(rendered_template)  # Print the template to debug

        # Print the rendered template for debugging
        print(rendered_template)


if __name__ == '__main__':
    unittest.main()
