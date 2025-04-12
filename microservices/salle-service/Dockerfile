FROM python:3.9
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY app ./app
COPY wsgi.py .

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]
