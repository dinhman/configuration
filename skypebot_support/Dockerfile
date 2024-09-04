FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libpq-dev \
    libjpeg-dev \
    freetds-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

COPY . .
# Copy the .env file
COPY .env .env

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV SFTP_HOST=119.82.135.233 \
    SFTP_PORT=2022 \
    SFTP_USER=man.dinh \
    SFTP_PASSWORD=ucLMYXTr433nungv \
    SKYPE_USER=vidbot2024@outlook.com \
    SKYPE_PWD=dhPzF3meW6$5u8NA \
    SKYPE_GROUP=19:d63482d4e9df41ff811e2fbc4d952447@thread.skype \
    DB_SERVER=172.16.1.10 \
    DB_USER=man.dinh \
    DB_PASSWORD=QTcC82HDzvJh \
    DB_NAME=localDB

CMD ["python", "main.py"]
