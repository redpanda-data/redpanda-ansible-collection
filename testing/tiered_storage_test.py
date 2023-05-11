import unittest
import os
from jinja2 import Environment, FileSystemLoader


class TestMyTemplate(unittest.TestCase):

    def setUp(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        relative_template_dir = os.path.join(script_dir, '..', 'roles', 'redpanda_broker', 'templates', 'configs', )
        self.env = Environment(loader=FileSystemLoader(relative_template_dir))

    def test_my_template(self):
        template = self.env.get_template('tiered_storage.j2')

        # no GCP while using creds
        rendered_output = template.render(cloud_storage_access_key='taco',
                                          cloud_storage_secret_key='mako',
                                          tiered_storage_bucket_name='pako',
                                          cloud_storage_region="us-west-2",
                                          cloud_storage_enable_remote_read="true",
                                          cloud_storage_enable_remote_write="true",
                                          cloud_storage_segment_max_upload_interval_sec="1")
        expected_output = '''cluster:
  cloud_storage_access_key: taco
  cloud_storage_secret_key: mako
  cloud_storage_enable_remote_read: true
  cloud_storage_enable_remote_write: true
  cloud_storage_region: us-west-2
  cloud_storage_bucket: pako
  cloud_storage_segment_max_upload_interval_sec: 1
  # cloud_storage_enabled must be after other cloud_storage parameters
  cloud_storage_enabled: True'''

        self.assertEqual(expected_output, rendered_output)

        # no gcp while using metadata
        rendered_output = template.render(cloud_storage_credentials_source="aws_instance_metadata",
                                          tiered_storage_bucket_name='pako',
                                          cloud_storage_region="us-west-2",
                                          cloud_storage_enable_remote_read="true",
                                          cloud_storage_enable_remote_write="true",
                                          cloud_storage_segment_max_upload_interval_sec="1")
        expected_output = '''cluster:
  cloud_storage_credentials_source: aws_instance_metadata
  cloud_storage_enable_remote_read: true
  cloud_storage_enable_remote_write: true
  cloud_storage_region: us-west-2
  cloud_storage_bucket: pako
  cloud_storage_segment_max_upload_interval_sec: 1
  # cloud_storage_enabled must be after other cloud_storage parameters
  cloud_storage_enabled: True'''

        self.assertEqual(expected_output, rendered_output.strip())

        # gcp while using metadata
        rendered_output = template.render(cloud_storage_credentials_source="aws_instance_metadata",
                                          tiered_storage_bucket_name='pako',
                                          cloud_storage_region="us-west-2",
                                          cloud_storage_enable_remote_read="true",
                                          cloud_storage_enable_remote_write="true",
                                          cloud_storage_segment_max_upload_interval_sec="1",
                                          tiered_storage_cloud_provider="gcp")
        expected_output = '''cluster:
  cloud_storage_api_endpoint: storage.googleapis.com
  cloud_storage_credentials_source: aws_instance_metadata
  cloud_storage_enable_remote_read: true
  cloud_storage_enable_remote_write: true
  cloud_storage_region: us-west-2
  cloud_storage_bucket: pako
  cloud_storage_segment_max_upload_interval_sec: 1
  # cloud_storage_enabled must be after other cloud_storage parameters
  cloud_storage_enabled: True'''

        self.assertEqual(expected_output, rendered_output.strip())
       # gcp while using metadata
        rendered_output = template.render(cloud_storage_credentials_source="aws_instance_metadata",
                                          tiered_storage_bucket_name='pako',
                                          cloud_storage_region="us-west-2",
                                          cloud_storage_segment_max_upload_interval_sec="1")
        expected_output = '''cluster:
  cloud_storage_credentials_source: aws_instance_metadata
  cloud_storage_region: us-west-2
  cloud_storage_bucket: pako
  cloud_storage_segment_max_upload_interval_sec: 1
  # cloud_storage_enabled must be after other cloud_storage parameters
  cloud_storage_enabled: True'''

        self.assertEqual(expected_output, rendered_output.strip())


if __name__ == '__main__':
    unittest.main()
