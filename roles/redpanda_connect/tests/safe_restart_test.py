import http.server
import json
import os
import shutil
import tempfile
import threading

import pytest
import ansible_runner


INVENTORY = """\
[connect]
node1 ansible_connection=local
"""

HEALTH_PORT = 18083
HEALTH_TASK = 'Wait for Kafka Connect REST API to be healthy'


class HealthHandler(http.server.BaseHTTPRequestHandler):
    requests_seen = []

    def do_GET(self):
        HealthHandler.requests_seen.append(self.path)
        body = json.dumps([]).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


@pytest.fixture()
def health_server():
    HealthHandler.requests_seen = []
    server = http.server.HTTPServer(('127.0.0.1', HEALTH_PORT), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    thread.join(timeout=5)


class TestSafeRestartHealthCheck:

    def test_health_check_runs_on_single_host_play(self, health_server):
        """The post-restart health check must run even with one play host.

        The old ansible_play_hosts | length > 1 gate skipped the REST health
        check for single-node plays, so exactly the deployments with no
        redundancy got no verification that Connect came back.
        """
        work_dir = tempfile.mkdtemp()
        inv = os.path.join(work_dir, 'inventory')
        with open(inv, 'w') as f:
            f.write(INVENTORY)

        try:
            r = ansible_runner.run(
                playbook='/app/tests/safe_restart.yml',
                inventory=inv,
                extravars={
                    'restart_required': True,
                    'connect_tls_enabled': False,
                    'rest_port': HEALTH_PORT,
                    'connect_restart_health_check_retries': 2,
                    'connect_restart_health_check_delay': 1,
                },
                cmdline='--tags connect_restart_health_check',
                quiet=False,
            )
            assert r.status == 'successful', f"Playbook failed: {r.rc}"

            outcome = None
            for event in r.events:
                if event.get('event_data', {}).get('task', '') == HEALTH_TASK:
                    if event['event'] in ('runner_on_ok', 'runner_on_skipped', 'runner_on_failed'):
                        outcome = event['event']
            assert outcome == 'runner_on_ok', \
                f"health check must run and succeed on a single-host play, got {outcome!r}"
            assert '/connectors' in HealthHandler.requests_seen, \
                f"health check must hit the REST API, saw {HealthHandler.requests_seen}"
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
