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

CMD ["python", "main.py"]
