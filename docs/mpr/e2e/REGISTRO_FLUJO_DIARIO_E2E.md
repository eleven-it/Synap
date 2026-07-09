# Registro E2E — Flujo diario MPR (tablero → imputación)

**Fecha de validación:** 09/07/2026  
**Base:** `administranet96`  
**Comando:** `docker exec Synap_app python manage.py e2e_mpr_trazabilidad --base administranet96`

## Caso de prueba

| Rol | IDArt | Descripción |
|-----|-------|-------------|
| Pack terminado | 127 | 2401 TM Atomik Media Liso Negro 2P |
| Componente (BOM 2×) | 1138 | 2401 T4 Atomik Media Liso Negro Logo Blanco 1Par |

**Pedidos PED vinculados (pack 127):**

| PED | Cod. mov. | Cant. packs |
|-----|-----------|-------------|
| 0001-00000005 | 50 | 200 |
| 0001-00000006 | 100 | 1.000 |
| 0001-00000007 | 117 | 1.000 |

La demanda del tablero es **agregada** de todos los PED; la imputación FIFO asignó al más antiguo (PED 0001-00000005).

## Cantidades de la prueba

| Etapa | Cantidad |
|-------|----------|
| Envío a fabricación | 24 pares |
| Parte de producción | 24 pares |
| CC → Semi elaborado | 20 pares |
| CC → 2da selección | 4 pares |
| Armado 1ra | 10 packs (−20 semi) |
| Imputación | 10 packs → PED 50 |

## Saldos pivot MPR (componente 1138)

| Fase | Producción | Semi | 2da | Terminado (pack 127) |
|------|------------|------|-----|----------------------|
| Inicial | 0 | 120 | 23 | 1.194 |
| Tras parte (+24) | 24 | 120 | 23 | 1.194 |
| Tras CC | 0 | 140 | 27 | 1.194 |
| Tras armado (−20 semi, +10 pack) | 0 | 120 | 27 | 1.204 |
| Tras imputación | 0 | 120 | 27 | 1.204 *(sin cambio físico)* |

## Veredicto

| Etapa | Stock coherente |
|-------|-----------------|
| Envío (virtual) | ✅ Sin movimiento físico |
| Parte | ✅ +Producción |
| Control de calidad | ✅ Transferencia Producción → Semi/2da |
| Armado | ✅ −Semi, +Terminado pack |
| Imputación | ✅ Trazabilidad `mpr_imputacion_armado`; stock sin cambio |

## Uso del comando

```bash
# Solo snapshot inicial (no muta datos)
docker exec Synap_app python manage.py e2e_mpr_trazabilidad --base administranet96 --dry-run

# Flujo completo con cantidades personalizadas
docker exec Synap_app python manage.py e2e_mpr_trazabilidad \
  --base administranet96 \
  --cant-envio 24 --cant-parte 24 \
  --cant-semi 20 --cant-2da 4 --cant-armado 10
```

**Nota:** El armado 1ra exige `lineas` BOM en el payload (misma regla que la UI del tablero de armado).

## Referencias

- Manual de usuario §11.1: [MANUAL_USUARIO_MPR.md](../MANUAL_USUARIO_MPR.md)
- Reportes cadena pipeline (4 etapas): [REPORTES_MPR.md](../REPORTES_MPR.md)
