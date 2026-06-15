# Menggunakan base image Python 3.14 versi slim agar ringan
FROM python:3.14-rc-slim

# Mengatur folder kerja di dalam container Docker
WORKDIR /app

# Menyalin file requirements terlebih dahulu untuk efisiensi cache layer
COPY requirements.txt .

# Upgrade pip internal container dan install semua library asli dari lokal laptop Anda
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Menyalin seluruh sisa file kodingan dari project ke dalam container
COPY . .

# Eksekusi perintah untuk menjalankan FastAPI via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]