# Ansible Collection for Redpanda

Redpanda Ansible Collection that enables provisioning and managing a [Redpanda](https://www.redpanda.com/) cluster.

## Usage

### Required Steps: Deploying Redpanda

More information on consuming this collection is [available here](https://docs.redpanda.com/docs/deploy/deployment-option/self-hosted/manual/production/production-deployment-automation/) in our official documentation. 

You can also see some example playbooks in our [deployment-automation](https://github.com/redpanda-data/deployment-automation/tree/main/ansible) repository. 

### Creating and Publishing the Collection

Bump `version` in `galaxy.yml`, commit it, and publish from that commit:

```shell
make publish
```

`make publish` is the only supported way to release. It builds the artifact from a `git archive` of `HEAD`, so only
committed files can ship, refuses an artifact that carries any dot-path, and uploads that verified artifact. It
prompts for an [API key from Ansible Galaxy](https://galaxy.ansible.com/me/preferences) without echoing it; set
`ANSIBLE_GALAXY_API_KEY` to skip the prompt. You need
[appropriate permissions](https://galaxy.ansible.com/docs/contributing/namespaces.html#adding-administrators-to-a-namespace)
on the namespace.

Do not run `ansible-galaxy collection build` in a working tree and publish the result: it packages the whole
directory, including untracked and gitignored local state. To inspect an artifact without publishing it, run
`make verify-artifact`; the result lands in `dist/`.

## SASL Authentication

```yaml
kafka_enable_authorization: true
sasl_superuser_username: "admin"
sasl_superuser_password: "secure-password"

schema_registry_service_user: "schema_registry_client"
schema_registry_service_password: "secure-password"
pandaproxy_service_user: "pandaproxy_client"
pandaproxy_service_password: "secure-password"
```

Mixed authentication (internal no-auth, external SASL):

```yaml
redpanda_kafka_listeners:
  - address: "{{ private_ip }}"
    port: 9092
    name: "internal"
    authentication_method: "none"
  - address: "0.0.0.0"
    port: 9093
    name: "external"
    authentication_method: "sasl"
```

Enterprise features (requires license):

```yaml
schema_registry_enable_authorization: true
redpanda_license_file: "{{ playbook_dir }}/redpanda.license"
admin_api_require_auth: true
```

See `user_management` role for managing users and ACLs.

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
