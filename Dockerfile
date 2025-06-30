# Usamos la imagen oficial de Python
FROM python:3.10

# Establecer directorio de trabajo en el contenedor
WORKDIR /app

# Instalar Node.js y npm
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# Verificar la instalación de Node.js y npm
RUN node -v && npm -v

RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    python3-dev \
    gettext

# Actualizar certificados de CA del sistema operativo
RUN apt-get update && apt-get install -y ca-certificates && update-ca-certificates

# Copiar los archivos al contenedor
COPY requirements.txt requirements.txt

# Instalar dependencias y forzar la reinstalación de certifi
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --upgrade --force-reinstall certifi

# Configurar variables de entorno para Firebase
#ENV FIREBASE_CREDENTIALS_PATH=/app/firebase_credentials.json

# Copia la clave privada de Firebase (asegúrate de tenerla en tu máquina local)
COPY firebase_credentials.json /app/firebase_credentials.json

# Exponer el puerto del API
EXPOSE 8000

RUN mkdir /app/staticfiles

# Copiar el resto del código del proyecto
COPY . .

# Comando por defecto para ejecutar Django
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "django_project.wsgi:application"]

