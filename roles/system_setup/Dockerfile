# Used for testing System Setup Role
FROM python:latest

WORKDIR /app

COPY tests/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# keep the apt lists: the spec test runs the role in check mode and
# the apt module needs a populated cache to resolve package names
RUN apt-get update && apt-get install -y python3-apt

COPY . .

CMD ["make", "do"]
