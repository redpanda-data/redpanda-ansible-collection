# Redpanda Connect Role

Installs Redpanda Connect. Currently in a limited alpha release.

## Overriding Config Files

There's a few different ways we're doing this as the files themselves are very different in structure and purpose.

For the connect-distributed file we're providing two default files that can be merged together for TLS. Then we allow the user to merge in whatever they want through an environment variable.

For the log4j and logging.properties file we allow straight content replace and only straight content replace as these are text files that do not need per-host modification.

For the jmx exporter file we're able to offer more complex merge and replace functionality as it is json and json dict merging is well supported in ansible.

For the systemd unit we allow passing in additional options to the kafka system but nothing much else

For the environment file named java-home we're allowing the user to provide additional values that can be appended after the existing ones.
