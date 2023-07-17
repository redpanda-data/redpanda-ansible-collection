## System Setup for Redpanda Clusters

Handles system configuration on individual brokers for a Redpanda cluster. This entails:
* copying over certs
* handling the configuration of the data directory
* ensuring the data directory has correct permissions
* installing dependencies on the node required for Redpanda to run

If you handle this with a prebuilt node image and/or internal tooling you don't need to include this role in any plays. 
