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
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(self.current_dir, '..', 'templates/configs')
        self.defaults_file = os.path.join(self.current_dir, '..', 'defaults', 'main.yml')

        # Load the defaults from the YAML file
        with open(self.defaults_file, 'r') as f:
            self.defaults = yaml.safe_load(f)

        # Create a Jinja2 environment with recursive undefined handling
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            undefined=RecursiveUndefined
        )

        # Add a custom filter for recursive rendering
        self.env.filters['recursive_render'] = self.recursive_render

        self.maxDiff = None
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

    def test_redpanda_template_tls(self):
        template = self.env.get_template('tls.j2')

        # First pass: render the template
        first_pass = template.render(
            hostvars=self.hostvars,
            groups=self.groups,
            inventory_hostname='35.91.106.231',
            **self.defaults
        )

        # Second pass: resolve any remaining Jinja2 expressions
        rendered_template = self.env.from_string(first_pass).render(**self.defaults)

        expected_rendered_values = {
            "node": {
                "redpanda": {
                    "admin_api_tls": {
                        "enabled": True,
                        "require_client_auth": False,
                        "key_file": "/etc/redpanda/certs/node.key",
                        "cert_file": "/etc/redpanda/certs/node.crt",
                        "truststore_file": "/etc/redpanda/certs/truststore.pem"
                    },
                    "kafka_api_tls": [
                        {
                            "name": "internal",
                            "enabled": True,
                            "require_client_auth": False,
                            "key_file": "/etc/redpanda/certs/node.key",
                            "cert_file": "/etc/redpanda/certs/node.crt",
                            "truststore_file": "/etc/redpanda/certs/truststore.pem"
                        }
                    ],
                    "rpc_server_tls": {
                        "enabled": True,
                        "require_client_auth": False,
                        "key_file": "/etc/redpanda/certs/node.key",
                        "cert_file": "/etc/redpanda/certs/node.crt",
                        "truststore_file": "/etc/redpanda/certs/truststore.pem"
                    }
                },
                "rpk": {
                    "tls": {
                        "enabled": True,
                        "ca": "/etc/redpanda/certs/truststore.pem"
                    },
                    "admin_api": {
                        "tls": {
                            "enabled": True,
                            "ca_file": "/etc/redpanda/certs/truststore.pem",
                            "truststore_file": "/etc/redpanda/certs/truststore.pem"
                        }
                    },
                    "kafka_api": {
                        "tls": {
                            "enabled": True,
                            "ca_file": "/etc/redpanda/certs/truststore.pem",
                            "truststore_file": "/etc/redpanda/certs/truststore.pem"
                        }
                    }
                },
                "pandaproxy": {
                    "pandaproxy_api_tls": [
                        {
                            "enabled": True,
                            "require_client_auth": False,
                            "key_file": "/etc/redpanda/certs/node.key",
                            "cert_file": "/etc/redpanda/certs/node.crt",
                            "truststore_file": "/etc/redpanda/certs/truststore.pem"
                        }
                    ]
                },
                "schema_registry": {
                    "schema_registry_api_tls": [
                        {
                            "enabled": True,
                            "require_client_auth": False,
                            "key_file": "/etc/redpanda/certs/node.key",
                            "cert_file": "/etc/redpanda/certs/node.crt",
                            "truststore_file": "/etc/redpanda/certs/truststore.pem"
                        }
                    ]
                }
            }
        }

        rendered_dict = yaml.safe_load(rendered_template)
        self.assertEqual(rendered_dict, expected_rendered_values)

        print(rendered_template)

    def test_redpanda_template_tls_without_custom_listeners(self):
        """Test TLS template without custom listeners (else branch).

        This is critical: when kafka_api_tls is an array, each entry must have
        a 'name' field to match with kafka_api listeners. Without this, Redpanda
        cannot properly match TLS configs to listeners, causing brokers to not
        advertise themselves in metadata responses.
        """
        template = self.env.get_template('tls.j2')

        # Create defaults without redpanda_kafka_listeners to trigger the else branch
        defaults_no_listeners = {k: v for k, v in self.defaults.items()
                                  if k != 'redpanda_kafka_listeners'}
        defaults_no_listeners['kafka_enable_authorization'] = False

        first_pass = template.render(
            hostvars=self.hostvars,
            groups=self.groups,
            inventory_hostname='35.91.106.231',
            **defaults_no_listeners
        )

        rendered_template = self.env.from_string(first_pass).render(**defaults_no_listeners)

        rendered_dict = yaml.safe_load(rendered_template)

        # Verify kafka_api_tls is an array with exactly one entry
        kafka_api_tls = rendered_dict['node']['redpanda']['kafka_api_tls']
        self.assertIsInstance(kafka_api_tls, list)
        self.assertEqual(len(kafka_api_tls), 1)

        # Critical: verify the entry has a 'name' field even without SASL
        self.assertIn('name', kafka_api_tls[0],
                     "kafka_api_tls entry must have 'name' field for listener matching")
        self.assertEqual(kafka_api_tls[0]['name'], 'default',
                        "kafka_api_tls entry should have name 'default'")
        self.assertTrue(kafka_api_tls[0]['enabled'])

        print(rendered_template)

if __name__ == '__main__':
    unittest.main()
