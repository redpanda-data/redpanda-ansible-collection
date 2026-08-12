# Used for testing Redpanda Roles
FROM python:latest

WORKDIR /app

# Copy the current directory contents into the container at /app
COPY tests/requirements.txt /app/requirements.txt

# Install Ansible and other dependencies
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y shellcheck bats && rm -rf /var/lib/apt/lists/*

COPY tests/requirements.yml /app/requirements.yml
RUN ansible-galaxy collection install -r requirements.yml --force
RUN ansible-galaxy role install -r requirements.yml --force

COPY . .

# Mock modules are staged outside the /app volume mount so they never leak
# onto the host role directory (see the Makefile mocks target)
ENV ANSIBLE_LIBRARY=/opt/mock-library

# Run make do when the container launches
CMD ["make", "do"]
