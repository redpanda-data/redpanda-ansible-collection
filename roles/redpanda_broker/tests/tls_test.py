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
                    "kafka_api_tls": {
                        "enabled": True,
                        "require_client_auth": False,
                        "key_file": "/etc/redpanda/certs/node.key",
                        "cert_file": "/etc/redpanda/certs/node.crt",
                        "truststore_file": "/etc/redpanda/certs/truststore.pem"
                    },
                    "rpc_server_tls": {
                        "enabled": True,
                        "require_client_auth": False,
                        "key_file": "/etc/redpanda/certs/node.key",
                        "cert_file": "/etc/redpanda/certs/node.crt",
                        "truststore_file": "/etc/redpanda/certs/truststore.pem"
                    }
                },
                "rpk": {
                    "admin_api": {
                        "tls": {
                            "truststore_file": "/etc/redpanda/certs/truststore.pem"
                        }
                    },
                    "kafka_api": {
                        "tls": {
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

if __name__ == '__main__':
    unittest.main()
