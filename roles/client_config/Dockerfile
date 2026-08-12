# Used for testing the client_config role
FROM python:latest

WORKDIR /app

COPY tests/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# python3-apt + unzip + kept apt lists: the spec test runs the real role
# against file:// fixtures and the package module needs working apt bindings
RUN apt-get update && apt-get install -y python3-apt unzip

COPY . .

CMD ["make", "do"]
