# Used for testing the demo_certs role
FROM python:latest

WORKDIR /app

COPY tests/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# keytool for truststore generation
RUN apt-get update && apt-get install -y default-jre-headless && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["make", "do"]
