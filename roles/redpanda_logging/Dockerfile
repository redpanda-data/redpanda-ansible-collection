# Used for testing Redpanda Roles
FROM python:latest

WORKDIR /app

# Copy requirements first (for better caching)
COPY tests/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire role
COPY . .

# Run make do when container launches
CMD ["make", "do"]