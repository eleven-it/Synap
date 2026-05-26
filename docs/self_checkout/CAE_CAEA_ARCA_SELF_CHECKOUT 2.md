# CAE y CAEA en Self-Checkout (ARCA/AFIP)

## Según documentación ARCA

- **CAE** (Código de Autorización Electrónico): se solicita en el momento de la emisión, vía Web Services. Requiere conexión con AFIP en ese instante.
- **CAEA** (Código de Autorización Electrónico Anticipado): régimen de contingencia. Se solicita por período quincenal (días 1-15 o 16-último del mes) **dentro de los 5 días corridos previos al inicio del período**. Permite facturar con ese código; los comprobantes se informan a ARCA (registro informativo) y se sincronizan dentro de los 8 días posteriores al cierre del período.

**CAEA entra cuando falla CAE**: ante fallas de Web Service o conectividad, se usa CAEA como contingencia. Cuando la conexión con ARCA se restablece, los comprobantes emitidos con CAEA se sincronizan (registro informativo).

## Obtención y renovación automática de CAEA

- **Ventanas de solicitud**: Período 1 (días 1-15) se puede solicitar los días 27, 28, 29, 30 y 31 del mes anterior. Período 2 (días 16-fin) se puede solicitar los días 11, 12, 13, 14 y 15 del mismo mes.
- **Almacenamiento**: Los CAEA obtenidos se guardan en `fe_afip.CAEACode` por `base_empresa`, `periodo` (YYYYMM) y `orden` (1 o 2).
- **Comando diario**: `python manage.py request_caea_auto` revisa si hoy está en alguna ventana; para cada configuración AFIP activa solicita (Consultar o Solicitar) y guarda el CAEA si aún no existe. Ejemplo para cron: `0 8 * * * cd /ruta/proyecto && python manage.py request_caea_auto`.
- **Uso en facturación**: En contingencia, el autoservicio usa primero el CAEA almacenado; si no hay, intenta CAEAConsultar/CAEASolicitar en tiempo real.

## Sincronización de numeración con ARCA

Antes de reservar el número de comprobante en `talonarios`, si AFIP está configurado se consulta en ARCA el **último comprobante autorizado** (FECompUltimoAutorizado) para el punto de venta y tipo (FA/FB). El próximo número local debe coincidir con “último en AFIP + 1”; si no coincide, la confirmación se rechaza con mensaje claro y se hace rollback (sin afectar talonarios). Así se evita desfase entre administraNET, self-checkout y ARCA cuando el mismo PV comparte numeración.

## Recuperación de CAE cuando la respuesta se pierde

Si se envía CAESolicitar y ARCA autoriza pero la conexión se corta antes de que Synap reciba la respuesta, en ARCA queda un CAE asignado y en Synap no. En ese caso:

1. **Tras error de red o excepción** en la solicitud de CAE, Synap intenta **recuperar el CAE** llamando a **FECompConsultar** (por punto de venta, tipo y número de comprobante). Si AFIP devuelve el comprobante con CAE, se usa ese CAE y la operación se completa con éxito (commit, actualización de cuentacliente).
2. Si la recuperación no devuelve CAE, se sigue con el flujo de contingencia CAEA (si aplica) o se devuelve error y rollback.

Módulo: `self_checkout/fe_sync.py` (`get_ultimo_autorizado_afip`, `consultar_cae_comprobante`).

## Restricción en Synap

Ningún comprobante puede guardarse sin CAE o, en su defecto, CAEA. Si no se obtiene ninguno de los dos, la operación se interrumpe y se hace **rollback** (no se afectan stock ni numeraciones).

---

## Flujo en el autoservicio (pantallas y modales)

Qué ve el usuario en cada situación y qué opciones tiene. Los detalles técnicos se indican entre paréntesis para referencia.

### Estado normal (conexión AFIP OK)

```
┌─────────────────────────────────────────┐
│  Autoservicio operativo                 │
│  El usuario compra, paga y confirma.    │
│  En cada confirmación: CAE en tiempo    │
│  real. Sin overlays ni modales.         │
└─────────────────────────────────────────┘
```

- **Pantalla:** Interfaz habitual del autoservicio (carrito, pago, confirmación).
- **Al confirmar:** Se solicita CAE a ARCA; si todo va bien, se muestra el comprobante/ticket y la venta queda cerrada.
- *(Healthcheck a AFIP cada 60 s — GET `/api/self-checkout/afip-health/`. Si responde OK, no se muestra ningún modal de contingencia.)*

---

### Conexión con AFIP caída: pantalla "Fuera de servicio"

Cuando el healthcheck falla, el autoservicio muestra una **pantalla completa (overlay)** que bloquea el uso normal:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│     ⚠  Fuera de servicio                                │
│     Conexión con AFIP caída.                            │
│                                                         │
│     ● Reintentando conexión en 10 s…  (cuenta atr)      │
│                                                         │
│     ┌─────────────────┐  ┌─────────────────────────┐    │
│     │  Pasar a CAEA   │  │  Solicitar asistencia   │    │
│     └─────────────────┘  └─────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

- **Qué ve el usuario:** Mensaje de "Fuera de servicio" y un indicador de reintento (cuenta regresiva cada 10 s).
- **Botón "Pasar a CAEA":** Permite seguir operando en modo contingencia (facturación con CAEA). Solo para supervisor o tras ingresar credenciales de supervisor en un modal.
- **Botón "Solicitar asistencia":** Acción a definir (ej. notificar a soporte).
- *(Overlay controlado por `afipOnline === false` y `caeaMode === false`. Reintento vía `checkAfipHealth()` cuando la cuenta llega a 0.)*

---

### Si el usuario elige "Pasar a CAEA"

**Si es supervisor/administrador:** Se llama a `POST /api/self-checkout/afip-caea-mode/` con `enable: true`. El overlay desaparece y el autoservicio vuelve a ser usable en modo contingencia.

**Si no es supervisor:** Se abre un **modal** pidiendo **credenciales de supervisor**. Si son correctas (`POST /api/self-checkout/supervisor-authorize-caea/` contra administraNET), se autoriza el modo CAEA, se cierra el modal y el overlay "Fuera de servicio" desaparece. Si falla, se muestra error en el modal.

---

### Durante la confirmación en modo CAEA

- **Pantalla:** Flujo normal de confirmación (sin overlay de "Fuera de servicio").
- **Detrás:** Se intenta CAE; si falla por red, se usa CAEA. Si no se obtiene ni CAE ni CAEA, la venta no se confirma (rollback) y se muestra un **modal de error**.
- **Modal de fallo:** Mensaje de que no se pudo completar por falta de autorización AFIP (código `AFIP_UNAVAILABLE`). Botones: "Solicitar asistencia" y "Cerrar".

---

### Cuando la conexión con AFIP vuelve

- El healthcheck vuelve a responder OK.
- El sistema **sale automáticamente** del estado "fuera de línea" y, si estaba en modo CAEA por contingencia, **sale también del modo CAEA** (vuelta a operación normal con CAE).
- **Pantalla:** Vuelta a la interfaz normal; el usuario no tiene que hacer nada.

**Resumen del flujo:**

```
     AFIP OK ──────────────► Autoservicio normal (CAE en cada venta)
          │
          │ healthcheck falla
          ▼
     Overlay "Fuera de servicio"
          │
          ├─ Reintento cada 10 s ──► Si AFIP responde ──► Vuelta a normal (automática)
          │
          └─ "Pasar a CAEA" (supervisor o login supervisor)
                    │
                    ▼
             Autoservicio operativo en contingencia (CAEA)
                    │
                    │ healthcheck vuelve a OK
                    ▼
             Vuelta a normal con CAE (automática)
```

