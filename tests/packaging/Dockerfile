# Used for testing what the Galaxy artifact contains
FROM python:3.14

WORKDIR /app

COPY tests/packaging/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# The tests read the checkout's tracked files through git, and the checkout
# is mounted from a host whose user differs from the container's.
RUN git config --global --add safe.directory /app

ENV PYTHONDONTWRITEBYTECODE=1

CMD ["make", "test-packaging"]
