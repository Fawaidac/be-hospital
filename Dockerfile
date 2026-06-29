FROM python:3.14-rc-slim

WORKDIR /app

# Pasang compiler lengkap khusus untuk Python 3.14 supaya bisa compile scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    make \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Upgrade pip, paksa install numpy duluan, baru install sisanya dari requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy==2.5.0 && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]