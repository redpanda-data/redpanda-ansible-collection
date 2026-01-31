# User Management Role

Idempotent management of SASL users, RBAC roles, and ACLs for Redpanda clusters.

## Features

- **Idempotent operations**: Queries existing state before making changes
- **User management**: Create, update passwords, and delete SASL users
- **Role management**: Create and delete RBAC roles (Enterprise)
- **Role membership**: Assign users to roles
- **Kafka ACLs**: Manage ACLs for topics, groups, cluster, and transactional IDs
- **Schema Registry ACLs**: Manage ACLs for SR subjects and global access (Enterprise)

## Requirements

- Redpanda cluster with SASL authentication enabled
- Admin user credentials with sufficient permissions
- For RBAC roles: Redpanda Enterprise license
- For Schema Registry ACLs: `schema_registry_enable_authorization: true`

## Role Variables

### Connection Settings

```yaml
redpanda_kafka_port: 9092
enable_tls: false
redpanda_truststore_file: "/etc/redpanda/certs/truststore.pem"
sasl_admin_username: "admin"
sasl_admin_password: "change-me"
sasl_mechanism: "SCRAM-SHA-256"
```

### User Definitions

```yaml
sasl_users:
  # Create a user
  - username: "producer_app"
    password: "secure-password"
    mechanism: "SCRAM-SHA-256"  # optional
    state: present              # optional, default is present

  # Update an existing user's password
  - username: "existing_user"
    password: "new-password"
    update_password: true       # Required to update existing users

  # Delete a user
  - username: "old_user"
    state: absent
```

### Role Definitions (Enterprise)

```yaml
sasl_roles:
  # Create a role with members
  - name: "producers"
    state: present
    members:
      - "producer_app"
      - "batch_producer"

  # Delete a role
  - name: "old_role"
    state: absent
```

### Kafka ACL Definitions

ACLs can be granted to either principals (users) or roles (Enterprise RBAC).
The `operation` and `resource_name` fields can be strings or lists for multiple values.

```yaml
sasl_acls:
  # Topic ACL - single operation
  - principal: "User:producer_app"
    resource_type: topic
    resource_name: "events-"      # Use with prefixed for wildcards
    pattern_type: prefixed        # literal or prefixed
    operation: write              # read, write, all, describe, create, delete, alter, etc.
    permission: allow             # allow or deny
    host: "*"                     # optional, defaults to *
    state: present

  # Multiple operations in one ACL
  - principal: "User:app_user"
    resource_type: topic
    resource_name: "app-topic"
    operation:                    # list of operations
      - read
      - write
      - describe
    permission: allow
    state: present

  # Multiple topics in one ACL
  - principal: "User:app_user"
    resource_type: topic
    resource_name:                # list of topics
      - "topic-a"
      - "topic-b"
      - "topic-c"
    operation: read
    permission: allow
    state: present

  # Role-based ACL (Enterprise RBAC)
  - role: "producers"             # use 'role' instead of 'principal'
    resource_type: topic
    resource_name: "events-"
    pattern_type: prefixed
    operation: write
    permission: allow
    state: present

  # Consumer group ACL
  - principal: "User:consumer_app"
    resource_type: group
    resource_name: "my-group"
    pattern_type: literal
    operation: read
    permission: allow
    state: present

  # Cluster ACL
  - principal: "User:admin_app"
    resource_type: cluster
    operation: all
    permission: allow
    state: present

  # Transactional ID ACL
  - principal: "User:producer_app"
    resource_type: transactional-id
    resource_name: "tx-"
    pattern_type: prefixed
    operation: write
    permission: allow
    state: present
```

### Schema Registry ACL Definitions (Enterprise)

Schema Registry ACLs also support role-based access and multiple operations/subjects.

```yaml
schema_registry_acls:
  # Subject ACL
  - principal: "User:producer_app"
    resource_type: subject
    resource_name: "events-"
    pattern_type: prefixed
    operation: write
    permission: allow
    state: present

  # Multiple subjects and operations
  - principal: "User:app_user"
    resource_type: subject
    resource_name:
      - "orders-"
      - "payments-"
    operation:
      - read
      - write
    pattern_type: prefixed
    permission: allow
    state: present

  # Role-based Schema Registry ACL (Enterprise RBAC)
  - role: "schema_admins"
    resource_type: global
    operation: all
    permission: allow
    state: present

  # Global Schema Registry ACL
  - principal: "User:schema_admin"
    resource_type: global
    operation: all
    permission: allow
    state: present
```

## Example Playbook

```yaml
---
- name: Manage SASL Users and ACLs
  hosts: redpanda[0]
  become: true
  vars:
    enable_tls: true
    sasl_admin_username: "admin"
    sasl_admin_password: "{{ lookup('env', 'REDPANDA_SASL_PASSWORD') }}"

    sasl_users:
      - username: "myapp"
        password: "{{ lookup('env', 'MYAPP_PASSWORD') }}"
        state: present

    sasl_acls:
      - principal: "User:myapp"
        resource_type: topic
        resource_name: "myapp-"
        pattern_type: prefixed
        operation: all
        permission: allow
        state: present

  roles:
    - role: redpanda.cluster.user_management
```

## Idempotency

This role is fully idempotent:

1. **Users**: Only creates users that don't exist. Only deletes users marked `state: absent` that exist. Password updates require `update_password: true`.

2. **Roles**: Only creates roles that don't exist. Only deletes roles marked `state: absent` that exist.

3. **ACLs**: Handles "already exists" gracefully when creating. Handles "not found" gracefully when deleting.

4. **Safe by default**: The admin user is protected and cannot be deleted.

## Running Multiple Times

You can safely run this role multiple times. On subsequent runs:
- Existing users/roles/ACLs with `state: present` are skipped (no change)
- Missing users/roles/ACLs are created
- Users/roles/ACLs with `state: absent` that exist are deleted

## External Configuration

You can define users, roles, and ACLs in a separate YAML file and pass it to the playbook:

```bash
ansible-playbook manage-sasl-users.yml -e @users.yml
```

Where `users.yml` contains:

```yaml
sasl_users:
  - username: "app1"
    password: "secret1"
    state: present

sasl_acls:
  - principal: "User:app1"
    resource_type: topic
    resource_name: "app1-"
    pattern_type: prefixed
    operation: all
    permission: allow
    state: present
```

## Security Best Practices

1. **Never commit passwords**: Use Ansible Vault or environment variables
2. **Least privilege**: Grant only necessary permissions
3. **Separate service accounts**: Use dedicated accounts for different applications
4. **Regular audits**: Review user permissions periodically

## License

Apache-2.0
