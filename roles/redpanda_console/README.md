# Ansible Deployment for Redpanda Console

## TLS Certificate Migration Note

If you manage TLS certificates outside of this role (`handle_cert_install: false`), you must ensure:


1**Console on dedicated node (no broker):**
   - Set certificate ownership to `redpanda-console:redpanda-console`
   - Set key file permissions to `0600`


2**Console co-located with Redpanda broker:**

This is not a recommended model for running a production cluster You will need a solution that allows both redpanda-console and redpanda to read their certs whether that be shared ownership or separate directories. 
