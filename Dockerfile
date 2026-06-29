FROM python:3.14-rc-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    make \
    gfortran \
    ninja-build \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install build tools
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install meson tools untuk scikit-learn
RUN pip install --no-cache-dir meson-python meson ninja cython

# Install numpy DULU, verifikasi bisa diimport
RUN pip install --no-cache-dir "numpy==2.3.0" && \
    python -c "import numpy; print('numpy OK:', numpy.__version__)"

# Install scikit-learn secara terpisah dengan build isolation dimatikan
RUN pip install --no-cache-dir --no-build-isolation scikit-learn==1.7.2

# Install sisanya (tanpa numpy & scikit-learn agar tidak konflik)
RUN pip install --no-cache-dir --no-build-isolation \
    $(grep -v -E "^(numpy|scikit-learn)" requirements.txt | tr '\n' ' ')

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]