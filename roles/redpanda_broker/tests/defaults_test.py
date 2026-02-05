import unittest
import os
import yaml
from jinja2 import Environment, FileSystemLoader, Undefined

class RecursiveUndefined(Undefined):
    def __getattr__(self, name):
        if name == 'undefined_name':
            return self._undefined_name
        return RecursiveUndefined(name=f'{self._undefined_name}.{name}')

    def __str__(self):
        return '{{ %s }}' % self._undefined_name

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

        # Create a Jinja2 environment with recursive undefined handling
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            undefined=RecursiveUndefined
        )

        # Add Ansible's bool filter
        def bool_filter(value):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', 'yes', '1')
            return bool(value)

        self.env.filters['bool'] = bool_filter

        # Add a custom filter for recursive rendering
        self.env.filters['recursive_render'] = self.recursive_render

        self.maxDiff = None

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

    def recursive_render(self, template_string):
        template = self.env.from_string(template_string)
        return template.render(**self.defaults)

    def test_redpanda_template_default_listener(self):
        # Load the template from file
        template = self.env.get_template('defaults.j2')

        # First pass: render the template
        first_pass = template.render(
            hostvars=self.hostvars,
            groups=self.groups,
            inventory_hostname='35.91.106.231',
            **self.defaults
        )

        # Second pass: resolve any remaining Jinja2 expressions
        rendered_template = self.env.from_string(first_pass).render(
            hostvars=self.hostvars,
            groups=self.groups,
            inventory_hostname='35.91.106.231',
            **self.defaults
        )

        # Convert the rendered template to a dictionary for easier comparison
        rendered_dict = yaml.safe_load(rendered_template)

        # When redpanda_kafka_listeners is defined (as in defaults), it uses those listeners
        # The listener should have a name from the defined listeners
        kafka_api = rendered_dict['node']['redpanda']['kafka_api']
        self.assertTrue(len(kafka_api) > 0)
        self.assertIn('name', kafka_api[0], "kafka_api listener must have a name")

        print(rendered_template)

    def test_redpanda_template_default_listener_no_custom_listeners(self):
        """Test that default listeners have 'name' field even without custom listeners or SASL.

        This is critical for TLS configurations where kafka_api_tls is an array
        and needs to match listeners by name.
        """
        template = self.env.get_template('defaults.j2')

        # Create defaults without redpanda_kafka_listeners and redpanda_advertised_kafka_listeners
        defaults_no_listeners = {k: v for k, v in self.defaults.items()
                                  if k not in ['redpanda_kafka_listeners', 'redpanda_advertised_kafka_listeners']}
        defaults_no_listeners['kafka_enable_authorization'] = False

        first_pass = template.render(
            hostvars=self.hostvars,
            groups=self.groups,
            inventory_hostname='35.91.106.231',
            **defaults_no_listeners
        )

        rendered_template = self.env.from_string(first_pass).render(
            hostvars=self.hostvars,
            groups=self.groups,
            inventory_hostname='35.91.106.231',
            **defaults_no_listeners
        )

        rendered_dict = yaml.safe_load(rendered_template)

        # Verify kafka_api has name even without SASL
        kafka_api = rendered_dict['node']['redpanda']['kafka_api']
        self.assertEqual(len(kafka_api), 1)
        self.assertEqual(kafka_api[0]['name'], 'default',
                        "kafka_api must have 'name: default' for TLS listener matching")
        self.assertNotIn('authentication_method', kafka_api[0],
                        "authentication_method should only be present with SASL")

        # Verify advertised_kafka_api has name even without SASL
        advertised_kafka_api = rendered_dict['node']['redpanda']['advertised_kafka_api']
        self.assertEqual(len(advertised_kafka_api), 1)
        self.assertEqual(advertised_kafka_api[0]['name'], 'default',
                        "advertised_kafka_api must have 'name: default' for TLS listener matching")
        self.assertNotIn('authentication_method', advertised_kafka_api[0],
                        "authentication_method should only be present with SASL")

        print(rendered_template)

    def test_advertised_kafka_api_inherits_names_from_kafka_listeners(self):
        """Test that advertised_kafka_api uses names from redpanda_kafka_listeners.

        When redpanda_kafka_listeners is defined but redpanda_advertised_kafka_listeners
        is not, advertised_kafka_api should derive listener names from redpanda_kafka_listeners
        to ensure they match. Mismatched names cause Redpanda to not advertise brokers properly.
        """
        template = self.env.get_template('defaults.j2')

        # Use defaults which have redpanda_kafka_listeners but NOT redpanda_advertised_kafka_listeners
        defaults_with_kafka_listeners = {k: v for k, v in self.defaults.items()
                                          if k != 'redpanda_advertised_kafka_listeners'}

        first_pass = template.render(
            hostvars=self.hostvars,
            groups=self.groups,
            inventory_hostname='35.91.106.231',
            **defaults_with_kafka_listeners
        )

        rendered_template = self.env.from_string(first_pass).render(
            hostvars=self.hostvars,
            groups=self.groups,
            inventory_hostname='35.91.106.231',
            **defaults_with_kafka_listeners
        )

        rendered_dict = yaml.safe_load(rendered_template)

        kafka_api = rendered_dict['node']['redpanda']['kafka_api']
        advertised_kafka_api = rendered_dict['node']['redpanda']['advertised_kafka_api']

        # Verify both have the same number of listeners
        self.assertEqual(len(kafka_api), len(advertised_kafka_api),
                        "kafka_api and advertised_kafka_api should have same number of listeners")

        # Verify names match between kafka_api and advertised_kafka_api
        for i, (ka, aka) in enumerate(zip(kafka_api, advertised_kafka_api)):
            self.assertEqual(ka['name'], aka['name'],
                           f"Listener {i}: kafka_api name '{ka['name']}' must match "
                           f"advertised_kafka_api name '{aka['name']}'")

        # Verify advertised_kafka_api uses advertised_ip (public) not private_ip
        self.assertEqual(advertised_kafka_api[0]['address'], '35.91.106.231',
                        "advertised_kafka_api should use advertised_ip")

    def test_sasl_with_default_listeners_has_authentication_method(self):
        """Test that authentication_method is set when kafka_enable_authorization=true
        and using default redpanda_kafka_listeners (which don't define authentication_method).

        This prevents ILLEGAL_SASL_STATE: when the cluster has SASL enabled but
        listeners lack authentication_method, Redpanda's SASL state machine
        doesn't initialize on those listeners.
        """
        template = self.env.get_template('defaults.j2')

        # Use defaults with SASL enabled but default listeners (no explicit authentication_method)
        defaults_sasl = dict(self.defaults)
        defaults_sasl['kafka_enable_authorization'] = True

        first_pass = template.render(
            hostvars=self.hostvars,
            groups=self.groups,
            inventory_hostname='35.91.106.231',
            **defaults_sasl
        )

        rendered_template = self.env.from_string(first_pass).render(
            hostvars=self.hostvars,
            groups=self.groups,
            inventory_hostname='35.91.106.231',
            **defaults_sasl
        )

        rendered_dict = yaml.safe_load(rendered_template)

        # Verify kafka_api has authentication_method: sasl
        kafka_api = rendered_dict['node']['redpanda']['kafka_api']
        self.assertEqual(len(kafka_api), 1)
        self.assertIn('authentication_method', kafka_api[0],
                      "kafka_api must have authentication_method when kafka_enable_authorization=true")
        self.assertEqual(kafka_api[0]['authentication_method'], 'sasl',
                        "authentication_method should default to 'sasl'")

        # Verify advertised_kafka_api also has authentication_method: sasl
        advertised_kafka_api = rendered_dict['node']['redpanda']['advertised_kafka_api']
        self.assertEqual(len(advertised_kafka_api), 1)
        self.assertIn('authentication_method', advertised_kafka_api[0],
                      "advertised_kafka_api must have authentication_method when kafka_enable_authorization=true")
        self.assertEqual(advertised_kafka_api[0]['authentication_method'], 'sasl',
                        "authentication_method should default to 'sasl'")

if __name__ == '__main__':
    unittest.main()
