"""
Test the data clearing logic by parsing the ACTUAL task file.
This prevents drift between test and implementation.
"""
import os
import pytest
import yaml
from jinja2 import Environment


def load_task_conditions():
    """Load the when conditions from the actual task file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    task_file = os.path.join(current_dir, '..', 'tasks', 'clear-data-for-sasl.yml')

    with open(task_file, 'r') as f:
        tasks = yaml.safe_load(f)

    # Find the "Clear data directory" task and extract its conditions
    for task in tasks:
        if 'Clear data directory' in task.get('name', ''):
            return task.get('when', [])

    raise ValueError("Could not find 'Clear data directory' task in clear-data-for-sasl.yml")


def evaluate_conditions(conditions, variables):
    """Evaluate Ansible when conditions using Jinja2."""
    env = Environment()

    # Add Ansible's default filter (simplified version)
    def default_filter(value, default_value=None):
        if value is None:
            return default_value
        return value

    # Add bool filter
    def bool_filter(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1')
        return bool(value)

    env.filters['default'] = default_filter
    env.filters['bool'] = bool_filter

    # Evaluate each condition
    for condition in conditions:
        # Handle 'not X.Y.Z' patterns
        template = env.from_string('{{ ' + condition + ' }}')
        result = template.render(**variables)
        # Jinja2 returns string, convert to bool
        if result.lower() in ('false', ''):
            return False

    return True


def should_clear_data(kafka_enable_authorization, package_changed, controller_exists, force_clear):
    """
    Evaluate whether data should be cleared using the ACTUAL conditions
    from clear-data-for-sasl.yml.
    """
    conditions = load_task_conditions()

    # Build the variable context that Ansible would have
    variables = {
        'kafka_enable_authorization': kafka_enable_authorization,
        'package_result': {'changed': package_changed},
        'controller_dir': {'stat': {'exists': controller_exists}},
        'sasl_force_clear_data_directory': force_clear,
    }

    return evaluate_conditions(conditions, variables)


@pytest.mark.parametrize("kafka_auth,pkg_changed,controller_exists,force,expected,description", [
    # Fresh install with SASL - should clear
    (True, True, False, False, True,
     "Fresh install with SASL enabled should clear data directory"),

    # Upgrade with existing data - should preserve
    (True, True, True, False, False,
     "Upgrade with existing cluster data should preserve data directory"),

    # Upgrade with force flag - should clear
    (True, True, True, True, True,
     "Upgrade with force flag should clear data directory even with existing data"),

    # SASL disabled - should preserve
    (False, True, False, False, False,
     "SASL disabled should preserve data directory"),

    # Idempotent run (package not changed) - should preserve
    (True, False, False, False, False,
     "Idempotent run (package unchanged) should preserve data directory"),
])
def test_sasl_data_clear_conditions(kafka_auth, pkg_changed, controller_exists, force, expected, description):
    """Test that the conditions in clear-data-for-sasl.yml behave correctly."""
    result = should_clear_data(kafka_auth, pkg_changed, controller_exists, force)
    assert result == expected, f"{description}: expected {expected}, got {result}"


def test_task_file_exists():
    """Verify the task file we're testing actually exists."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    task_file = os.path.join(current_dir, '..', 'tasks', 'clear-data-for-sasl.yml')
    assert os.path.exists(task_file), f"Task file not found: {task_file}"


def test_task_file_has_expected_structure():
    """Verify the task file has the expected tasks."""
    conditions = load_task_conditions()
    assert len(conditions) == 3, f"Expected 3 conditions, got {len(conditions)}: {conditions}"

    # Verify key conditions are present (without checking exact syntax)
    condition_str = ' '.join(conditions)
    assert 'kafka_enable_authorization' in condition_str
    assert 'package_result' in condition_str
    assert 'controller_dir' in condition_str


def test_install_files_include_safeguard():
    """Verify both DEB and RPM install files use the safeguarded task."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for install_file in ['install-rp-deb.yml', 'install-rp-rpm.yml']:
        path = os.path.join(current_dir, '..', 'tasks', install_file)
        with open(path) as f:
            content = f.read()
        assert 'clear-data-for-sasl.yml' in content, \
            f"{install_file} must include clear-data-for-sasl.yml"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
