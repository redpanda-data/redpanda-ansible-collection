"""Filters for diffing desired SASL/ACL state against rpk-reported state.

ACLs are compared via normalized key strings of the form
principal|host|resource_type|resource_name|pattern_type|operation|permission
with case-insensitive principal/type/operation/permission matching, so a
desired entry is only (re)created when at least one of its expanded
combinations is missing from the cluster.
"""

import json


def _listify(value, default=None):
    if value is None:
        return [default] if default is not None else []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _norm_resource_type(rtype):
    return str(rtype or '').lower().replace('-', '_')


def _norm_key(principal, host, rtype, rname, pattern, operation, permission):
    return '|'.join([
        str(principal or '').lower(),
        str(host or '*'),
        _norm_resource_type(rtype),
        str(rname),
        str(pattern or 'literal').lower(),
        str(operation or '').lower(),
        str(permission or 'allow').lower(),
    ])


def user_management_acl_keys(existing_acls):
    """Normalize `rpk security acl list` matches into comparison keys."""
    keys = []
    for acl in existing_acls or []:
        if not isinstance(acl, dict):
            continue
        keys.append(_norm_key(
            acl.get('principal', ''),
            acl.get('host', '*'),
            acl.get('resource_type', ''),
            acl.get('resource_name', '*'),
            acl.get('pattern_type', 'literal'),
            acl.get('operation', ''),
            acl.get('permission', 'allow'),
        ))
    return keys


def user_management_acl_desired_keys(item):
    """Expand one sasl_acls entry into the comparison keys it implies."""
    if 'role' in item:
        principal = 'RedpandaRole:%s' % item['role']
    else:
        principal = item.get('principal', '')
    operations = _listify(item.get('operation'))
    if _norm_resource_type(item.get('resource_type')) == 'cluster':
        # rpk reports cluster ACLs against the fixed kafka-cluster resource
        resources = ['kafka-cluster']
    else:
        resources = _listify(item.get('resource_name'), default='*') or ['*']
    keys = []
    for op in operations:
        for res in resources:
            keys.append(_norm_key(
                principal,
                item.get('host', '*'),
                item.get('resource_type', ''),
                res,
                item.get('pattern_type', 'literal'),
                op,
                item.get('permission', 'allow'),
            ))
    return keys


def user_management_role_members(role_members_result, role_name):
    """Extract the current member names of a role from the registered
    results of the `rpk security role describe` loop."""
    for res in (role_members_result or {}).get('results') or []:
        item = res.get('item') or {}
        if not isinstance(item, dict) or item.get('name') != role_name:
            continue
        stdout = (res.get('stdout') or '').strip()
        if not stdout:
            return []
        try:
            data = json.loads(stdout)
        except ValueError:
            return []
        members = []
        for member in (data.get('members') or []):
            if isinstance(member, dict):
                members.append(member.get('name'))
            else:
                members.append(member)
        return members
    return []


class FilterModule(object):

    def filters(self):
        return {
            'user_management_acl_keys': user_management_acl_keys,
            'user_management_acl_desired_keys': user_management_acl_desired_keys,
            'user_management_role_members': user_management_role_members,
        }
