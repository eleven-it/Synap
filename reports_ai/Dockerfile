# Usar imagen base más reciente y ligera
FROM pytorch/pytorch:latest

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Directorio de trabajo
WORKDIR /app

# Consolidar todas las instalaciones de sistema en una sola capa
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # Dependencias de compilación (se purgarán después)
        build-essential \
        curl \
        git \
        libpq-dev \
        libffi-dev \
        libssl-dev \
        pkg-config \
        software-properties-common \
        # Limpieza completa
        && apt-get purge -y build-essential \
        && apt-get autoremove -y \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/* \
        && rm -rf /tmp/* \
        && rm -rf /var/tmp/*

# Copiar requirements antes del resto para aprovechar cache
COPY reports_ai/requirements_ai.txt requirements_ai.txt

# Instalar dependencias Python en una sola capa
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --timeout 300 -r requirements_ai.txt \
    && rm -rf ~/.cache/pip

# Copiar el proyecto
COPY reports_ai/ .

# Crear usuario no-root y cambiar permisos
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app

# Cambiar a usuario no-root
USER appuser

# Exponer puerto
EXPOSE 8000

# Comando optimizado
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"] 