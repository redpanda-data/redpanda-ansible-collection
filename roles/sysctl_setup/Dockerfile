# Used for testing the sysctl_setup role
FROM python:latest

WORKDIR /app

COPY tests/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["make", "do"]
