# Dockerfile personalizado para Qdrant con netcat para health checks
FROM qdrant/qdrant:latest

# Instalar netcat para health checks
RUN apt-get update \
    && apt-get install -y --no-install-recommends netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Mantener el entrypoint original de Qdrant
ENTRYPOINT ["./entrypoint.sh"] 