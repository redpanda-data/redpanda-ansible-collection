#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(
        argument_spec=dict(
            mock_type=dict(type='str', required=True, choices=['shell', 'template']),
            cmd=dict(type='str', required=False),
            mock_stdout=dict(type='str', required=False),
            mock_rc=dict(type='int', required=False),
            src=dict(type='str', required=False),
            dest=dict(type='str', required=False),
            owner=dict(type='str', required=False),
            group=dict(type='str', required=False),
            mode=dict(type='str', required=False),
            mock_changed=dict(type='bool', required=False)
        )
    )

    mock_type = module.params['mock_type']

    if mock_type == 'shell':
        mock_stdout = module.params['mock_stdout']
        mock_rc = module.params['mock_rc']

        if mock_rc == 0:
            module.exit_json(changed=False, stdout=mock_stdout, stderr='', rc=mock_rc)
        else:
            module.fail_json(msg="Command failed", stdout=mock_stdout, stderr='Command failed', rc=mock_rc)

    elif mock_type == 'template':
        mock_changed = module.params['mock_changed']
        module.exit_json(changed=mock_changed, dest=module.params['dest'])


if __name__ == '__main__':
    main()
