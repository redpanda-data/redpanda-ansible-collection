# Ansible Collection for Redpanda

Redpanda Ansible Collection that enables provisioning and managing a [Redpanda](https://www.redpanda.com/) cluster.

## Usage

### Required Steps: Deploying Redpanda

More information on consuming this collection is [available here](https://docs.redpanda.com/docs/deploy/deployment-option/self-hosted/manual/production/production-deployment-automation/) in our official documentation. 

You can also see some example playbooks in our [deployment-automation](https://github.com/redpanda-data/deployment-automation/tree/main/ansible) repository. 

### Creating and Publishing the Collection

To build the collection you first need to bump the version number listed in ansible/redpanda/cluster/galaxy.yml

You will probably
need [appropriate permissions](https://galaxy.ansible.com/docs/contributing/namespaces.html#adding-administrators-to-a-namespace)
on the namespace for this to work.

Once that's all sorted, run the following shell script with
an [API key from Ansible Galaxy](https://galaxy.ansible.com/me/preferences)


```shell
ansible-galaxy collection build
ansible-galaxy collection publish redpanda-cluster-*.tar.gz --token <YOUR_API_KEY> -s https://galaxy.ansible.com/api/
```

## Testing

### Running Tests

Python tests are located in `roles/*/tests/` directories. To run all tests:

```shell
# Install test dependencies (only needed once)
pipx install --include-deps pytest

# Run tests for specific roles
python3 roles/redpanda_broker/tests/defaults_test.py
python3 roles/redpanda_connect/tests/jmx-exporter-config_test.py
python3 roles/redpanda_console/tests/defaults_test.py
python3 roles/redpanda_logging/tests/backend_test.py

# For tests requiring pytest framework
pytest roles/redpanda_broker/tests/restart_required_test.py -v
```

### Test Dependencies

Some tests require additional dependencies beyond the basic Python standard library:
- `pytest` - Required for certain broker tests
- `jinja2` - Template rendering 
- `pyyaml` - YAML parsing
- `ansible-runner` - For integration tests

Install all test dependencies using the requirements files in each role's test directory.

## Troubleshooting

### On Mac OS X, Python unable to fork workers

If you see something like this:

```
ok: [34.209.26.177] => {“changed”: false, “stat”: {“exists”: false}}
objc[57889]: +[__NSCFConstantString initialize] may have been in progress in another thread when fork() was called.
objc[57889]: +[__NSCFConstantString initialize] may have been in progress in another thread when fork() was called. We cannot safely call it or ignore it in the fork() child process. Crashing instead. Set a breakpoint on objc_initializeAfterForkError to debug.
ERROR! A worker was found in a dead state
```

You might try resolving by setting an environment variable:
`export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`

See: https://stackoverflow.com/questions/50168647/multiprocessing-causes-python-to-crash-and-gives-an-error-may-have-been-in-progr
