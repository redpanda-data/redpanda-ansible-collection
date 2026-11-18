"""
Enabling kafka_enable_authorization on a cluster that already exists must
stop before anything changes unless the SASL superuser can be used.

The role creates the bootstrap superuser only when a cluster first starts
(RP_BOOTSTRAP_USER), but it applies `superusers` and `admin_api_require_auth`
to running clusters on every run. Without a guard, turning SASL on for an
existing cluster requires Admin API authentication for a user that doesn't
exist, and the run fails partway with the Admin API locked.

These tests run the real tasks/check-sasl-superuser.yml with ansible-playbook
against localhost. A stand-in `rpk` on PATH returns the output that
`rpk security user list` produces on a real cluster and records how it was
called. A stand-in Admin API answers the dry-run cluster config request the
way Redpanda does (observed on v26.2.6): while admin_api_require_auth is off,
a request with a wrong password is treated as anonymous, and enabling
admin_api_require_auth is accepted only from an authenticated superuser.
"""
import base64
import http.server
import json
import os
import stat
import subprocess
import sys
import threading

import pytest
import yaml

ROLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GUARD_TASKS = os.path.join(ROLE_DIR, 'tasks', 'check-sasl-superuser.yml')
START_TASKS = os.path.join(ROLE_DIR, 'tasks', 'start-redpanda.yml')

FAKE_RPK = """#!/bin/sh
printf 'args=%s\\n' "$*" >> "$FAKE_RPK_LOG"
printf 'RPK_USER=%s\\n' "$RPK_USER" >> "$FAKE_RPK_LOG"
printf '%b' "$FAKE_RPK_STDOUT"
printf '%b' "$FAKE_RPK_STDERR" >&2
exit "${FAKE_RPK_RC:-0}"
"""

# `rpk security user list` prints a USERNAME header, then one user per line.
USERS_WITHOUT_SUPERUSER = 'USERNAME\\nschema_registry_client\\n'
USERS_WITH_SUPERUSER = 'USERNAME\\nadmin\\nschema_registry_client\\n'
# A cluster that already requires Admin API auth rejects a wrong password.
WRONG_PASSWORD_STDERR = ('unable to list users: request GET '
                         'http://10.0.0.11:9644/v1/security/users failed: '
                         'Unauthorized, invalid credentials\\n')


SUPERUSER_REJECTED = {'admin_api_require_auth': 'May only be set by a superuser'}


class FakeAdminAPI(http.server.BaseHTTPRequestHandler):
    """An Admin API with admin_api_require_auth off and one SASL user."""

    def do_PUT(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
        self.server.requests.append({'path': self.path, 'body': body})
        # A wrong password isn't rejected; the request just becomes anonymous.
        user = None
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Basic '):
            name, _, password = base64.b64decode(auth[6:]).decode().partition(':')
            if self.server.users.get(name) == password:
                user = name
        upsert = body.get('upsert', {})
        if upsert.get('admin_api_require_auth') and user not in upsert.get('superusers', []):
            status, reply = 400, SUPERUSER_REJECTED
        else:
            status, reply = 200, {'config_version': 2}
        payload = json.dumps(reply).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


@pytest.fixture
def admin_api():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), FakeAdminAPI)
    server.users = {'admin': 'the-real-password'}
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


def run_guard(tmp_path, *, is_initialized, kafka_enable_authorization,
              rpk_stdout='', rpk_stderr='', rpk_rc=0, admin_api=None,
              password='not-the-real-password'):
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    rpk = bindir / 'rpk'
    rpk.write_text(FAKE_RPK)
    rpk.chmod(rpk.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / 'rpk.log'
    log.write_text('')

    # The node config of the running broker, as the role's templates write it.
    node_config = tmp_path / 'redpanda.yaml'
    admin_port = admin_api.server_address[1] if admin_api else 9644
    node_config.write_text(yaml.safe_dump({
        'redpanda': {'admin': [{'address': '127.0.0.1', 'port': admin_port}]},
        'rpk': {'admin_api': {'addresses': [f'127.0.0.1:{admin_port}']}},
    }))

    playbook = tmp_path / 'play.yml'
    playbook.write_text(yaml.safe_dump([{
        'hosts': 'localhost',
        'gather_facts': False,
        'tasks': [{'ansible.builtin.include_tasks': GUARD_TASKS}],
    }]))
    extra_vars = {
        'is_initialized': is_initialized,
        'kafka_enable_authorization': kafka_enable_authorization,
        'sasl_superuser_username': 'admin',
        'sasl_superuser_password': password,
        'redpanda_rpk_opts': f'--config {node_config}',
        'redpanda_broker_node_config_file': str(node_config),
        'redpanda_broker_no_log': False,
    }
    env = dict(os.environ,
               PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}",
               FAKE_RPK_LOG=str(log),
               FAKE_RPK_STDOUT=rpk_stdout,
               FAKE_RPK_STDERR=rpk_stderr,
               FAKE_RPK_RC=str(rpk_rc),
               ANSIBLE_LOCALHOST_WARNING='False',
               ANSIBLE_NOCOLOR='True')
    proc = subprocess.run(
        ['ansible-playbook', str(playbook), '-e', json.dumps(extra_vars)],
        env=env, capture_output=True, text=True)
    return proc, log.read_text()


def test_existing_cluster_without_superuser_fails_before_changing_anything(tmp_path):
    proc, rpk_log = run_guard(tmp_path, is_initialized=True, kafka_enable_authorization=True,
                              rpk_stdout=USERS_WITHOUT_SUPERUSER)
    assert proc.returncode != 0, proc.stdout
    assert "has no SASL user named 'admin'" in proc.stdout, proc.stdout
    assert 'rpk security user create admin' in proc.stdout, proc.stdout
    assert f"args=security user list --config {tmp_path / 'redpanda.yaml'}" in rpk_log


def test_existing_cluster_with_superuser_continues(tmp_path, admin_api):
    proc, rpk_log = run_guard(tmp_path, is_initialized=True, kafka_enable_authorization=True,
                              rpk_stdout=USERS_WITH_SUPERUSER, admin_api=admin_api,
                              password='the-real-password')
    assert proc.returncode == 0, proc.stdout
    assert 'RPK_USER=admin' in rpk_log
    assert admin_api.requests, 'the password was never checked'


def test_existing_cluster_with_a_wrong_superuser_password_fails(tmp_path, admin_api):
    # With Admin API authentication still off, listing users succeeds whatever the password is.
    proc, _ = run_guard(tmp_path, is_initialized=True, kafka_enable_authorization=True,
                        rpk_stdout=USERS_WITH_SUPERUSER, admin_api=admin_api,
                        password='not-the-real-password')
    assert proc.returncode != 0, proc.stdout
    assert "didn't accept the password for 'admin'" in proc.stdout, proc.stdout
    assert 'No cluster or node configuration was changed' in proc.stdout, proc.stdout
    assert 'not-the-real-password' not in proc.stdout


def test_the_password_check_only_sends_dry_run_requests(tmp_path, admin_api):
    run_guard(tmp_path, is_initialized=True, kafka_enable_authorization=True,
              rpk_stdout=USERS_WITH_SUPERUSER, admin_api=admin_api, password='the-real-password')
    assert admin_api.requests
    for request in admin_api.requests:
        assert request['path'] == '/v1/cluster_config?dry_run=true', request


def test_unreachable_admin_api_fails(tmp_path):
    # Nothing listens on the Admin API port of the node config.
    proc, _ = run_guard(tmp_path, is_initialized=True, kafka_enable_authorization=True,
                        rpk_stdout=USERS_WITH_SUPERUSER, password='the-real-password')
    assert proc.returncode != 0, proc.stdout
    assert "Couldn't check the password for 'admin'" in proc.stdout, proc.stdout


def test_existing_cluster_rejecting_the_credentials_fails(tmp_path):
    proc, _ = run_guard(tmp_path, is_initialized=True, kafka_enable_authorization=True,
                        rpk_stderr=WRONG_PASSWORD_STDERR, rpk_rc=1)
    assert proc.returncode != 0, proc.stdout
    assert "Couldn't list SASL users as 'admin'" in proc.stdout, proc.stdout
    assert 'invalid credentials' in proc.stdout, proc.stdout
    assert 'not-the-real-password' not in proc.stdout


@pytest.mark.parametrize('is_initialized,kafka_enable_authorization', [
    (False, True),   # new cluster: the bootstrap superuser is created on first start
    (True, False),   # SASL not requested
    (False, False),
])
def test_guard_does_not_run_when_it_does_not_apply(tmp_path, is_initialized, kafka_enable_authorization):
    proc, rpk_log = run_guard(tmp_path, is_initialized=is_initialized,
                              kafka_enable_authorization=kafka_enable_authorization,
                              rpk_rc=1)
    assert proc.returncode == 0, proc.stdout
    assert rpk_log == '', 'rpk should not be called'


def _task_index(tasks, predicate, what):
    for i, task in enumerate(tasks):
        if predicate(task):
            return i
    raise AssertionError(f'{what} not found in start-redpanda.yml')


def test_start_redpanda_runs_the_guard_before_changing_a_running_cluster():
    with open(START_TASKS) as f:
        tasks = yaml.safe_load(f)
    guard = _task_index(
        tasks,
        lambda t: str(t.get('ansible.builtin.include_tasks', '')).endswith('check-sasl-superuser.yml'),
        'include of check-sasl-superuser.yml')
    started = _task_index(tasks, lambda t: t.get('name') == 'Start redpanda (standard)',
                          "'Start redpanda (standard)'")
    cluster_config = _task_index(tasks, lambda t: t.get('name') == 'Set cluster config (for running cluster updates)',
                                 "'Set cluster config (for running cluster updates)'")
    node_config = _task_index(tasks, lambda t: t.get('name') == 'Generate Node config - post-bootstrap runs',
                              "'Generate Node config - post-bootstrap runs'")
    assert started < guard, 'the guard needs the cluster running to list users'
    assert guard < cluster_config, 'the guard must run before cluster config is applied'
    assert guard < node_config, 'the guard must run before node config is rewritten'


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v', '-p', 'no:cacheprovider']))
