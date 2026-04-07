# Used for testing Redpanda Console Role
FROM python:latest

WORKDIR /app

COPY tests/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["make", "do"]
