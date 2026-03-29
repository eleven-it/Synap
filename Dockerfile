# Usar imagen base más ligera
FROM python:3.10-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias básicas del sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # Dependencias básicas
        curl \
        gnupg2 \
        ca-certificates \
        pkg-config \
        # Dependencias de compilación
        build-essential \
        gcc \
        default-libmysqlclient-dev \
        python3-dev \
        gettext \
        # Node.js
        && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
        && apt-get install -y nodejs \
        && npm install -g npm@latest \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/* \
        && rm -rf /tmp/* \
        && rm -rf /var/tmp/*

# Verificar instalaciones
RUN node -v && npm -v

# Copiar requirements antes del resto para aprovechar cache de Docker
COPY requirements.txt .

# Python: incluye opencv-python-headless (preprocesado OCR Stage 1, factura compra).
# Instalar dependencias Python en una sola capa con optimizaciones
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --upgrade --force-reinstall certifi \
    && rm -rf ~/.cache/pip

# Limpiar herramientas de compilación después de instalar dependencias Python
RUN apt-get purge -y build-essential gcc python3-dev \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Tesseract OCR + idiomas spa/eng (OCR plano y TSV estructurado Stage 1, factura compra)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-spa \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio para archivos estáticos
RUN mkdir -p /app/staticfiles

# Copiar el resto del código del proyecto
COPY . .

# pyafipws en ./pyafipws (directorio local, en .gitignore): WSAA/WSFE y padrón A4–A5.
# pysimplesoap viene en requirements.txt; sin esta carpeta la imagen arranca pero FE/padrón no funcionan.
RUN if [ -f pyafipws/setup.py ] || [ -f pyafipws/pyproject.toml ]; then \
      pip install --no-cache-dir -e ./pyafipws; \
    else \
      echo "Synap: no hay pyafipws/ en el contexto de build; clonar en la raíz del repo: git clone https://github.com/reingart/pyafipws.git pyafipws"; \
    fi \
    && rm -rf ~/.cache/pip

# Copiar y hacer ejecutable el script de entrada
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Exponer puerto
EXPOSE 8000

# Comando por defecto optimizado
# Usar el script de entrada para inicialización automática
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

