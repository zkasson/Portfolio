FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libkrb5-dev \
    krb5-config \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .

CMD ["streamlit", "run", "app.py"]
