## Used for testing the Kafka Connect role
FROM python:latest

WORKDIR /app

# Bake the test dependencies into the image so `make do` / pytest runs
# don't reinstall ansible on every container start.
COPY tests/requirements.txt /app/tests/requirements.txt
RUN pip install --no-cache-dir -r tests/requirements.txt

COPY . .

CMD ["make", "do"]
