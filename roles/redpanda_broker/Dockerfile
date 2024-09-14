# Used for testing Redpanda Roles
FROM python:latest

WORKDIR /app

# Copy the current directory contents into the container at /app
COPY tests/requirements.txt /app/requirements.txt

# Install Ansible and other dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY tests/requirements.yml /app/requirements.yml
RUN ansible-galaxy collection install -r requirements.yml --force
RUN ansible-galaxy role install -r requirements.yml --force

COPY . .

# Set ANSIBLE_LIBRARY environment variable
ENV ANSIBLE_LIBRARY=/app/library

# Run make do when the container launches
CMD ["make", "do"]
