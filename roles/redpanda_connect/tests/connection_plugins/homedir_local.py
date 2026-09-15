# Test-only connection plugin.
#
# Executes tasks on the controller exactly like the builtin `local`
# connection, but forces the module working directory to the user's home
# directory. That is what a real ssh connection gives remote tasks, so a
# relative path in a module (e.g. `stat: path: tls/certs/...`) resolves
# against the remote user's home instead of the playbook directory. The
# builtin `local` connection runs modules from the playbook directory,
# which hides control-node/remote path-resolution bugs; this plugin makes
# them reproducible without a remote host.

from __future__ import annotations

DOCUMENTATION = """
    name: homedir_local
    short_description: local execution with the remote-home working directory ssh gives
    description:
        - Executes tasks on the controller like the local connection plugin, but with
          the working directory forced to the user's home directory, matching the cwd
          a real ssh connection gives remote tasks.
    author: redpanda
    options:
        become_success_timeout:
            type: int
            default: 10
            description:
                - Number of seconds to wait for become to succeed when enabled.
            vars:
                - name: ansible_local_become_success_timeout
        become_strip_preamble:
            type: bool
            default: true
            description:
                - Strip internal become output preceding command execution.
            vars:
                - name: ansible_local_become_strip_preamble
    extends_documentation_fragment:
        - connection_pipelining
"""

import os

from ansible.plugins.connection.local import Connection as LocalConnection


class Connection(LocalConnection):

    transport = 'homedir_local'

    @property
    def cwd(self):
        return os.path.expanduser('~')

    @cwd.setter
    def cwd(self, value):
        # Ansible sets the local connection's cwd to the playbook directory;
        # ignore that so relative paths keep resolving against the home
        # directory, as they would on an ssh-connected remote.
        pass
