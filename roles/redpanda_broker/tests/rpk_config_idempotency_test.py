import json
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("rpk"), "rpk not found — requires a running local cluster")
class TestRpkClusterConfigIdempotency(unittest.TestCase):
    """Validates rpk config get/set behavior for idempotent Ansible tasks.

    Requires a running local cluster: rpk container start -n 1

    Key findings:
    - rpk cluster config get returns 'null' for properties not explicitly set
      (even if they have a default in bootstrap.yaml)
    - rpk returns booleans as lowercase: 'true' / 'false'
    - rpk returns floats without trailing zeros: '0.8', '0.002'
    - rpk returns enums as plain lowercase strings: 'config_file', 'none'
    - rpk returns arrays as YAML multiline ('- item') or '[]' for empty
    - rpk cluster config set always exits 0 and always prints
      "Successfully updated configuration" even when value is unchanged
    - Therefore we MUST use a get-then-compare approach for idempotency
    """

    RPK = "rpk"

    def rpk(self, *args):
        result = subprocess.run(
            [self.RPK] + list(args),
            capture_output=True, text=True
        )
        return result

    def rpk_get(self, key):
        """Get a cluster config value, returning the trimmed string."""
        result = self.rpk("cluster", "config", "get", key)
        self.assertEqual(result.returncode, 0, f"rpk cluster config get {key} failed: {result.stderr}")
        return result.stdout.strip()

    def rpk_set(self, key, value):
        """Set a cluster config value."""
        result = self.rpk("cluster", "config", "set", key, str(value))
        self.assertEqual(result.returncode, 0, f"rpk cluster config set {key} {value} failed: {result.stderr}")
        return result

    @staticmethod
    def parse_yaml_array(rpk_output):
        """Parse rpk's YAML array output into a Python list.

        rpk returns arrays in two formats:
        - Empty: '[]'
        - Populated: YAML multiline with '- item' per line

        Returns a list of string values.
        """
        if rpk_output == "[]":
            return []
        lines = rpk_output.strip().splitlines()
        items = []
        for line in lines:
            if line.startswith("- "):
                items.append(line[2:].strip())
        return items

    @staticmethod
    def normalize_for_comparison(rpk_value, ansible_value):
        """Normalize rpk output and Ansible value for comparison.

        Handles type-specific formatting differences:
        - Booleans: rpk='true'/'false', Ansible='True'/'False'
        - Arrays: rpk=YAML multiline, Ansible=JSON list
        - Scalars: simple string comparison
        """
        rpk_str = rpk_value.strip()

        # Array: rpk returns YAML multiline or '[]'
        if rpk_str == "[]" or rpk_str.startswith("- "):
            rpk_list = TestRpkClusterConfigIdempotency.parse_yaml_array(rpk_str)
            if isinstance(ansible_value, list):
                ansible_list = [str(v) for v in ansible_value]
            else:
                ansible_list = json.loads(ansible_value) if isinstance(ansible_value, str) else [str(ansible_value)]
            return sorted(rpk_list), sorted(ansible_list)

        # Scalar: lowercase string comparison
        return rpk_str.lower(), str(ansible_value).lower()

    # --- Output format tests ---

    def test_get_unset_property_returns_null(self):
        """Properties not explicitly set via API can return 'null'.

        Note: Which properties return 'null' depends on whether they have
        a built-in default and whether they've been previously set via API.
        We use audit_log_replication_factor which typically has no default.
        """
        value = self.rpk_get("audit_log_replication_factor")
        print(f"Property with no default: {repr(value)}")
        # Properties without a built-in default return 'null'
        # Properties with defaults (like kafka_qdc_depth_alpha=0.8) return the default
        self.assertIn(value, ["null", "0"],
                      "Expected 'null' for unset or '0' if previously set")

    def test_get_nullable_string_returns_null(self):
        """Nullable string properties return 'null' when unset."""
        value = self.rpk_get("cloud_storage_bucket")
        print(f"Nullable string property: {repr(value)}")
        # cloud_storage_bucket defaults to null when not configured
        self.assertEqual(value, "null",
                         "Expected 'null' for unset nullable string")

    def test_get_boolean_returns_lowercase(self):
        """rpk returns booleans as lowercase 'true'/'false' for both values."""
        # Test a boolean that defaults to false
        value_false = self.rpk_get("enable_rack_awareness")
        print(f"Boolean (default false): {repr(value_false)}")
        self.assertIn(value_false, ["true", "false"])

        # Test a boolean that defaults to true
        value_true = self.rpk_get("auto_create_topics_enabled")
        print(f"Boolean (default true): {repr(value_true)}")
        self.assertIn(value_true, ["true", "false"])

        # Test SASL-related boolean
        value_sasl = self.rpk_get("enable_sasl")
        print(f"Boolean (enable_sasl): {repr(value_sasl)}")
        self.assertIn(value_sasl, ["true", "false"])

    def test_get_float_returns_decimal(self):
        """rpk returns floats as decimal strings without trailing zeros."""
        # Standard decimal: 0.8
        value_alpha = self.rpk_get("kafka_qdc_depth_alpha")
        print(f"Float (depth_alpha): {repr(value_alpha)}")
        try:
            float_val = float(value_alpha)
            self.assertIsInstance(float_val, float)
        except ValueError:
            self.fail(f"Expected float-parseable string, got {repr(value_alpha)}")
        # Verify no trailing zeros (0.8 not 0.80)
        if value_alpha != "null":
            self.assertNotRegex(value_alpha, r'\.\d+0$',
                                "Float should not have trailing zeros")

        # Small decimal: 0.002
        value_latency = self.rpk_get("kafka_qdc_latency_alpha")
        print(f"Float (latency_alpha): {repr(value_latency)}")
        if value_latency != "null":
            try:
                float(value_latency)
            except ValueError:
                self.fail(f"Expected float-parseable string, got {repr(value_latency)}")

    def test_get_enum_returns_string(self):
        """rpk returns enum values as plain lowercase strings."""
        value_creds = self.rpk_get("cloud_storage_credentials_source")
        print(f"Enum (credentials_source): {repr(value_creds)}")
        # config_file is the default
        self.assertTrue(value_creds.islower() or value_creds == "null",
                        f"Expected lowercase enum string, got {repr(value_creds)}")

        value_schema = self.rpk_get("enable_schema_id_validation")
        print(f"Enum (schema_id_validation): {repr(value_schema)}")
        valid_enum_values = ["none", "redpanda", "compat", "null"]
        self.assertIn(value_schema, valid_enum_values,
                      f"Expected one of {valid_enum_values}, got {repr(value_schema)}")

    def test_get_array_returns_yaml_format(self):
        """rpk returns arrays as YAML multiline or '[]' for empty."""
        # Empty array
        value_empty = self.rpk_get("superusers")
        print(f"Array (empty, superusers): {repr(value_empty)}")
        parsed_empty = self.parse_yaml_array(value_empty)
        self.assertIsInstance(parsed_empty, list)

        # Populated array - audit_enabled_event_types has defaults
        value_populated = self.rpk_get("audit_enabled_event_types")
        print(f"Array (populated, audit_enabled_event_types): {repr(value_populated)}")
        if value_populated != "[]" and value_populated != "null":
            self.assertTrue(value_populated.startswith("- "),
                            f"Expected YAML multiline format, got {repr(value_populated)}")
            parsed = self.parse_yaml_array(value_populated)
            self.assertGreater(len(parsed), 0,
                               "Populated array should have elements")
            print(f"  Parsed array items: {parsed}")

        # Single-element array - http_authentication defaults to [BASIC]
        value_single = self.rpk_get("http_authentication")
        print(f"Array (single, http_authentication): {repr(value_single)}")
        if value_single not in ["[]", "null"]:
            parsed_single = self.parse_yaml_array(value_single)
            print(f"  Parsed single-element array: {parsed_single}")

    # --- Roundtrip tests (set then get) ---

    def test_set_then_get_integer_roundtrip(self):
        """After explicit set, get returns the value as a string."""
        original = self.rpk_get("rpc_server_tcp_recv_buf")

        self.rpk_set("rpc_server_tcp_recv_buf", "65536")
        value = self.rpk_get("rpc_server_tcp_recv_buf")
        self.assertEqual(value, "65536")

        # Test large integer
        self.rpk_set("kafka_batch_max_bytes", "1048576")
        value_large = self.rpk_get("kafka_batch_max_bytes")
        self.assertEqual(value_large, "1048576")

        # Test small integer
        self.rpk_set("default_topic_partitions", "1")
        value_small = self.rpk_get("default_topic_partitions")
        self.assertEqual(value_small, "1")

        # Restore
        if original != "null":
            self.rpk_set("rpc_server_tcp_recv_buf", original)

    def test_set_then_get_boolean_roundtrip(self):
        """Boolean roundtrip preserves lowercase format."""
        original = self.rpk_get("enable_rack_awareness")

        self.rpk_set("enable_rack_awareness", "false")
        self.assertEqual(self.rpk_get("enable_rack_awareness"), "false")

        self.rpk_set("enable_rack_awareness", "true")
        self.assertEqual(self.rpk_get("enable_rack_awareness"), "true")

        # Restore
        self.rpk_set("enable_rack_awareness", original)

    def test_set_then_get_float_roundtrip(self):
        """Float roundtrip preserves decimal format."""
        original_alpha = self.rpk_get("kafka_qdc_depth_alpha")

        # Set standard decimal
        self.rpk_set("kafka_qdc_depth_alpha", "0.8")
        value = self.rpk_get("kafka_qdc_depth_alpha")
        self.assertEqual(value, "0.8",
                         f"Expected '0.8' after set, got {repr(value)}")

        # Set different float value
        self.rpk_set("kafka_qdc_depth_alpha", "0.5")
        value = self.rpk_get("kafka_qdc_depth_alpha")
        self.assertEqual(value, "0.5",
                         f"Expected '0.5' after set, got {repr(value)}")

        # Restore
        if original_alpha != "null":
            self.rpk_set("kafka_qdc_depth_alpha", original_alpha)

    def test_set_then_get_enum_roundtrip(self):
        """Enum roundtrip preserves string format."""
        original = self.rpk_get("cloud_storage_credentials_source")

        self.rpk_set("cloud_storage_credentials_source", "config_file")
        value = self.rpk_get("cloud_storage_credentials_source")
        self.assertEqual(value, "config_file",
                         f"Expected 'config_file' after set, got {repr(value)}")

        # Set to a different enum value
        self.rpk_set("cloud_storage_credentials_source", "aws_instance_metadata")
        value = self.rpk_get("cloud_storage_credentials_source")
        self.assertEqual(value, "aws_instance_metadata",
                         f"Expected 'aws_instance_metadata' after set, got {repr(value)}")

        # Restore
        if original != "null":
            self.rpk_set("cloud_storage_credentials_source", original)

    def test_set_then_get_array_roundtrip(self):
        """Array roundtrip: JSON input becomes YAML multiline output."""
        original = self.rpk_get("superusers")

        # Set array using JSON format (what Ansible would send)
        self.rpk_set("superusers", '["admin", "producer"]')
        value = self.rpk_get("superusers")
        print(f"Array after set: {repr(value)}")

        parsed = self.parse_yaml_array(value)
        self.assertEqual(sorted(parsed), ["admin", "producer"],
                         f"Expected ['admin', 'producer'], parsed: {parsed}")

        # Set to empty array
        self.rpk_set("superusers", "[]")
        value_empty = self.rpk_get("superusers")
        parsed_empty = self.parse_yaml_array(value_empty)
        self.assertEqual(parsed_empty, [],
                         f"Expected empty list, parsed: {parsed_empty}")

        # Restore
        if original not in ["[]", "null"]:
            self.rpk_set("superusers", original)
        else:
            self.rpk_set("superusers", "[]")

    # --- rpk set behavior tests ---

    def test_set_always_reports_success(self):
        """rpk set exits 0 and prints success even when value is unchanged."""
        self.rpk_set("enable_rack_awareness", "false")

        # Set same value again
        result = self.rpk_set("enable_rack_awareness", "false")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Successfully updated configuration", result.stdout)

    def test_set_output_identical_for_change_and_noop(self):
        """rpk set output does NOT distinguish between change and no-change.

        This confirms we cannot rely on rpk set output for idempotency -
        we must use a get-then-compare approach.
        """
        # Ensure a known value
        self.rpk_set("enable_rack_awareness", "false")

        # Set to different value (actual change)
        result_change = self.rpk_set("enable_rack_awareness", "true")

        # Set to same value (no-op)
        result_noop = self.rpk_set("enable_rack_awareness", "true")

        # Exit codes are the same
        self.assertEqual(result_change.returncode, result_noop.returncode)

        # Both say "Successfully updated" regardless
        self.assertIn("Successfully updated configuration", result_change.stdout)
        self.assertIn("Successfully updated configuration", result_noop.stdout)

        print(f"Change stdout: {repr(result_change.stdout)}")
        print(f"No-op stdout:  {repr(result_noop.stdout)}")

        # Restore
        self.rpk_set("enable_rack_awareness", "false")

    # --- Ansible comparison logic tests ---

    def test_comparison_after_explicit_set(self):
        """After values are explicitly set, get-then-compare works across all types."""
        test_configs = {
            # Integers
            "rpc_server_tcp_recv_buf": 65536,
            "kafka_batch_max_bytes": 1048576,
            "default_topic_partitions": 1,
            # Booleans
            "enable_rack_awareness": False,
            "auto_create_topics_enabled": True,
            # Floats
            "kafka_qdc_depth_alpha": 0.8,
            # Enums
            "cloud_storage_credentials_source": "config_file",
            "enable_schema_id_validation": "none",
        }

        # First, explicitly set all values (simulating first Ansible run)
        for key, value in test_configs.items():
            self.rpk_set(key, str(value).lower())

        # Now simulate second Ansible run comparison
        for key, desired_value in test_configs.items():
            current = self.rpk_get(key)
            desired_str = str(desired_value).lower()
            current_str = current.lower()
            needs_change = current_str != desired_str
            print(f"{key}: current={repr(current)}, desired={repr(desired_str)}, "
                  f"needs_change={needs_change}")
            self.assertFalse(needs_change,
                            f"{key} should not need change: "
                            f"rpk returned {repr(current)}, desired {repr(desired_str)}")

    def test_comparison_detects_actual_change(self):
        """Comparison correctly identifies when a value differs."""
        self.rpk_set("rpc_server_tcp_recv_buf", "65536")

        current = self.rpk_get("rpc_server_tcp_recv_buf")
        desired_str = str(32768).lower()
        current_str = current.lower()
        needs_change = current_str != desired_str
        self.assertTrue(needs_change,
                       "Should detect change needed from 65536 to 32768")

        # Restore
        self.rpk_set("rpc_server_tcp_recv_buf", "65536")

    def test_array_comparison_logic(self):
        """Array comparison requires parsing YAML multiline output.

        rpk returns arrays as YAML multiline ('- item' per line) but Ansible
        provides values as JSON lists. The comparison must parse both formats.
        """
        # Set a populated array
        self.rpk_set("superusers", '["admin", "producer"]')
        rpk_value = self.rpk_get("superusers")
        ansible_value = ["admin", "producer"]

        rpk_normalized, ansible_normalized = self.normalize_for_comparison(
            rpk_value, ansible_value)
        self.assertEqual(rpk_normalized, ansible_normalized,
                         f"Array comparison should match: rpk={rpk_normalized}, "
                         f"ansible={ansible_normalized}")

        # Test mismatch detection
        ansible_different = ["admin", "consumer"]
        rpk_normalized, ansible_normalized = self.normalize_for_comparison(
            rpk_value, ansible_different)
        self.assertNotEqual(rpk_normalized, ansible_normalized,
                            "Array comparison should detect mismatch")

        # Test empty array comparison
        self.rpk_set("superusers", "[]")
        rpk_empty = self.rpk_get("superusers")
        rpk_normalized, ansible_normalized = self.normalize_for_comparison(
            rpk_empty, [])
        self.assertEqual(rpk_normalized, ansible_normalized,
                         "Empty array comparison should match")

        # Test empty vs populated mismatch
        rpk_normalized, ansible_normalized = self.normalize_for_comparison(
            rpk_empty, ["admin"])
        self.assertNotEqual(rpk_normalized, ansible_normalized,
                            "Empty vs populated array should not match")

    def test_null_comparison_always_triggers_change(self):
        """When rpk returns 'null', comparison logic correctly triggers a set.

        On first Ansible run, cluster config properties haven't been set via
        the API yet. The get-then-compare approach will see 'null' != desired
        value and correctly trigger a set. This tests that logic directly.
        """
        # Simulate what Ansible sees when rpk returns 'null' for an unset property
        simulated_null = "null"

        test_desired_values = [
            "65536",        # integer
            "true",         # boolean true
            "false",        # boolean false
            "0.8",          # float
            "0.002",        # small float
            "config_file",  # enum
            "none",         # enum that looks like null but isn't
            "producer",     # string
        ]
        for desired in test_desired_values:
            needs_change = simulated_null.lower() != desired.lower()
            self.assertTrue(needs_change,
                            f"'null' should always differ from desired {repr(desired)}")


if __name__ == '__main__':
    unittest.main()
