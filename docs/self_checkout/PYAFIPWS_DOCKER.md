# pyafipws, Docker y padrón AFIP (FA/FB)

## Resumen

- **Synap** usa `self_checkout.services.padron_afip_service.consultar_condicion_fiscal` (Padrón A5 con fallback A4) y WSFE vía **pyafipws**.
- **`pysimplesoap`** es dependencia obligatoria del cliente SOAP del padrón (`pyafipws.ws_sr_padron`). Sin ella aparece `No module named 'pysimplesoap'` y el padrón no se carga.
- **`future`** (paquete PyPI `future`): la cadena de imports de pyafipws/pysimplesoap puede requerirla; sin ella aparece `No module named 'future'`. Va en `requirements.txt` junto a `pysimplesoap`.
- **`pyafipws`** no se sube al repo: la carpeta **`pyafipws/`** en la raíz del proyecto está en `.gitignore`. Se espera un clon local de [reingart/pyafipws](https://github.com/reingart/pyafipws).

## Instalación local (sin Docker)

En la raíz del repo Synap:

```bash
git clone https://github.com/reingart/pyafipws.git pyafipws
pip install -r requirements.txt
pip install -e ./pyafipws
```

`requirements.txt` incluye `pysimplesoap`; el editable `-e ./pyafipws` aporta `wsaa`, `wsfev1`, `ws_sr_padron`, etc.

## Docker

El **Dockerfile**, después de `COPY . .`, ejecuta:

- Si existe `pyafipws/setup.py` o `pyafipws/pyproject.toml` → `pip install -e ./pyafipws`.
- Si no hay carpeta (p. ej. build desde CI sin clonar) → mensaje en build; la app arranca pero **FE y padrón no funcionan** hasta reconstruir con `pyafipws/` presente en el contexto de build.

**Importante:** `pyafipws/` no está en `.dockerignore`, así que si existe en el host al hacer `docker build`, se copia e instala.

## Condiciones para que el padrón responda

1. **`pysimplesoap` instalado** y **`pyafipws` instalado** (editable desde `./pyafipws` o equivalente).
2. **Certificado, clave y CUIT** del emisor configurados (`fe_afip.AFIPConfig` por `base_empresa` o variables `AFIP_*`). Ver `self_checkout/fe_config.py`.
3. **CUIT consultado** válido (11 dígitos).
4. En **ARCA/AFIP**, el certificado debe tener autorizado el web service **Padrón A5** y/o **A4** (WSAA pide ticket para `ws_sr_padron_a5` o `ws_sr_padron_a4`).
5. **Conectividad** a los endpoints de homologación o producción definidos en `padron_afip_service.py`.

## Kiosco / TPV

Si el padrón no está disponible por dependencias o error de import, `consultar_cuit` puede devolver `padron_no_disponible` y el aviso **"Validación AFIP no disponible. Se usará Factura B."**; el flujo sigue con FB. Misma función usa **captura factura compra** para resolver proveedor contra AFIP cuando no hay registro en AdministraNET.
