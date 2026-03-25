# OCR Stage 1.5 — Revisión de build e infraestructura

## Contexto

Paso de **reproducibilidad** antes de Stage 2: asegurar que las dependencias del Stage 1 (OpenCV vía pip, Tesseract vía sistema) entran por la ruta de build oficial, no solo por estado manual del contenedor.

## Qué se instalaba manualmente antes

En entornos donde la imagen Docker **no** se reconstruyó tras añadir `opencv-python-headless` a `requirements.txt`, era posible que el contenedor en ejecución **no** tuviera el paquete hasta ejecutar a mano:

```bash
docker exec Synap_app pip install 'opencv-python-headless>=4.8,<5'
```

Eso **no** queda registrado en la imagen: al recrear el contenedor sin rebuild, el estado podía perderse según cómo se genere la imagen.

## Qué es reproducible en build actual

| Dependencia | Ruta oficial | Ubicación en repo |
|-------------|--------------|-------------------|
| **OpenCV (Python)** | `pip install -r requirements.txt` | `requirements.txt` línea `opencv-python-headless>=4.8,<5` |
| **Tesseract + spa + eng** | `apt-get` en imagen | `Dockerfile`: bloque `tesseract-ocr`, `tesseract-ocr-spa`, `tesseract-ocr-eng` |
| **Bindings Python** | `pip` | `pytesseract` en `requirements.txt` |

El **`Dockerfile`** raíz:

1. Copia `requirements.txt` e instala dependencias Python (incluye OpenCV headless).
2. Tras limpiar herramientas de compilación, instala los paquetes **apt** de Tesseract e idiomas.

`docker-compose.yml` declara `build: .` para el servicio `app`, por lo que **`docker compose build app`** aplica esta receta.

## Compose y rebuild limpio

- **Suficiente** para Stage 1: `Dockerfile` + `requirements.txt` + bloque apt de Tesseract.
- Un **rebuild limpio** típico:

```bash
docker compose build --no-cache app
docker compose up -d app
```

(El nombre del servicio puede variar; en este repo el servicio principal es `app`.)

## Riesgos restantes

1. **Desalineación imagen vs código:** el volumen `.:/app` monta el código host; las dependencias pip siguen siendo las de la **imagen**. Si solo se actualiza `requirements.txt` en host y no se reconstruye la imagen, faltarán paquetes hasta hacer `build`.
2. **Otros Dockerfiles:** existe `support/backend/Dockerfile`; el alcance de Stage 1 OCR de factura compra es el **`Dockerfile`** raíz del proyecto Synap principal.
3. **CI/CD externo:** si el pipeline no usa este `Dockerfile`, debe declarar explícitamente las mismas dependencias (pip + apt) o una imagen base equivalente.

## Cambios aplicados en esta revisión

- Comentarios en el **`Dockerfile`** que enlazan OpenCV (pip) y Tesseract + idiomas (apt) con el OCR de factura compra Stage 1, para futuras auditorías sin releer todo el archivo.
