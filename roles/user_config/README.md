## Ansible Role: SASL Users and ACLs Manager
This Ansible role is designed to manage Redpanda Cluster SASL users and ACLs. It provides the capability to create and delete users as well as their permissions.

## Requirements
Ansible 2.x

## Security Considerations

### Admin Credentials
Ensure that the sasl_admin_username and sasl_admin_password are secure and are not hardcoded in the playbook

### Password Management: 
Ensure that passwords are managed securely. You can use a base64 encoded JSON object passed through the CLI to ensure secure password passthrough.

## Role Variables

| Variable                       | Description                                                                                   | Default                |
|--------------------------------|-----------------------------------------------------------------------------------------------|------------------------|
| `sasl_mechanism`               | The SASL mechanism to be used.                                                                | `SCRAM-SHA-256`        |
| `acl_user_create`              | A switch to toggle between creating or deleting.                                              | `true`                 |
| `delete_users`                 | Set this to true to enable user deletion.                                                     | `false`                |
| `delete_permissions`           | Set this to true to enable permissions deletion.                                              | `false`                |
| `sasl_admin_username`          | Admin username, used for authentication.                                                      | `admin`                |
| `sasl_admin_password`          | Admin password, used for authentication.                                                      | `password`             |
| `user_password_map_create`     | A yaml map containing the user, password, and permissions to create.                          | see defaults/main.yaml |
| `user_password_map_delete`     | A yaml map containing the user, password, and permissions to delete.                          | see defaults/main.yaml |
| `base64_encoded_up_map_create` | An override for user_password_map_create that enables passing in a base64 encoded JSON object | -                      | 
| `base64_encoded_up_map_delete` | An override for user_password_map_delete that enables passing in a base64 encoded JSON object | -                      | 

### Using the base64_encoded_up_map overrides

To ensure there are no merge issues and to make clear the difference the role will accept as overrides for user_password_map_{create,delete}. 

The intention here is to provide a CI friendly passthrough option. 

For convenience, here is a one-liner to generate properly base64 encoded JSON for these variables. Note that you must have JQ installed:

```shell
jq -c . input.json | tr -d '\n' | base64
```
