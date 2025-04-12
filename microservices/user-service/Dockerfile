FROM python:3.9
WORKDIR /app

# Installer les dépendances système
RUN apt-get update && \
    apt-get install -y netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copier l'application
COPY . .

# Spécifier la commande (peut être écrasée par docker-compose)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]
