# Spec — Conteo móvil ciego (PWA)

**Capability:** `stock-inventario-fisico-conteo-movil`
**Change:** `stock-inventario-fisico`
**Estado:** Propuesto

---

## Purpose

Permitir a operarios registrar conteos físicos desde PWA móvil (Nivel A): escaneo EAN/código + cantidad, progreso de avance y feedback operativo, en modo **conteo ciego** sin exposición de saldo de sistema ni diferencias.

---

## Requirements

### Requirement: Conteo ciego obligatorio

Las APIs y la UI orientadas al rol contador MUST NOT exponer `saldo_snapshot`, saldo de sistema, diferencia calculada ni indicadores que revelen desvío respecto al stock. El contador MUST ver únicamente identificación del artículo (código, EAN, descripción) y la cantidad que ingresa.

#### Scenario: Respuesta API sin datos de saldo

- **GIVEN** un operario autenticado con `stock.inventario_fisico.contar` en campaña asignada
- **WHEN** consulta el detalle de un artículo o envía un conteo vía API de conteo
- **THEN** la respuesta MUST NOT incluir campos `saldo_snapshot`, `saldo_sistema`, `diferencia` ni equivalentes

#### Scenario: UI móvil sin columnas de saldo

- **GIVEN** un operario en `/stock/conteo/` de una campaña activa
- **WHEN** escanea o busca un artículo
- **THEN** la pantalla muestra código/descripción y campo de cantidad, sin saldo ni diferencia

#### Scenario: Intento de filtración por error de servidor

- **GIVEN** un endpoint de conteo configurado correctamente
- **WHEN** un test automatizado inspecciona payloads hacia rol contador
- **THEN** MUST NOT encontrar claves de saldo o diferencia en ningún nivel anidado

---

### Requirement: Captura EAN/código y cantidad

El flujo principal MUST permitir escanear código de barras (EAN) o ingresar código manualmente, confirmar artículo y registrar cantidad contada. El sistema SHOULD reutilizar el patrón de escáner de `alta_movimiento` y la resolución de artículos por código existente.

#### Scenario: Escaneo EAN válido en campaña

- **GIVEN** un artículo de la campaña con EAN registrado
- **WHEN** el operario escanea el EAN e ingresa cantidad 12
- **THEN** el conteo queda registrado para ese artículo y operario en menos de 8 segundos con catálogo prefetched

#### Scenario: Código no pertenece a la campaña

- **GIVEN** un código de artículo ajeno al universo de la campaña
- **WHEN** el operario intenta registrar conteo
- **THEN** el sistema rechaza con mensaje claro en español sin revelar saldos

#### Scenario: Cantidad inválida

- **GIVEN** un artículo válido seleccionado
- **WHEN** el operario envía cantidad vacía, negativa o no numérica
- **THEN** el sistema MUST NOT persistir el conteo e informa el error en UI Synap (sin `alert` nativo)

---

### Requirement: Progreso de conteo visible al operario

La PWA MUST mostrar progreso del operario: artículos contados vs total asignado o catálogo de campaña, estado de sincronización (pendiente/sincronizado/conflicto) y última acción exitosa. MUST NOT mostrar métricas de diferencia global.

#### Scenario: Barra de progreso personal

- **GIVEN** un operario con 30 de 100 artículos contados en la campaña
- **WHEN** abre la pantalla principal de conteo
- **THEN** ve avance numérico o visual sin saldo ni diferencia de stock

#### Scenario: Indicador de sync pendiente

- **GIVEN** conteos en cola local sin red
- **WHEN** el operario consulta progreso
- **THEN** ve cantidad de eventos pendientes de sincronización

---

### Requirement: PWA Nivel A y whitelist

Las rutas de conteo móvil MUST estar en la whitelist PWA Nivel A (`pwa_nivel_a.py`, `MobileLevelAOnlyMiddleware`). El acceso desde navegador no autorizado MUST redirigir o denegar según política existente de Nivel A.

#### Scenario: Conteo desde PWA instalada

- **GIVEN** PWA Nivel A instalada y sesión válida de operario
- **WHEN** navega a `/stock/conteo/<campana>/`
- **THEN** carga la UI de conteo optimizada para móvil

#### Scenario: Acceso fuera de whitelist móvil

- **GIVEN** un cliente no incluido en whitelist Nivel A
- **WHEN** intenta acceder a `/stock/conteo/`
- **THEN** el middleware aplica la restricción definida para PWA Nivel A

---

### Requirement: UI canon Synap

Las pantallas de conteo MUST seguir el canon UI de reportes/MPR: Tailwind/Alpine, modales Synap, textos en español, fechas `dd/MM/yyyy`. MUST NOT usar `alert`, `confirm` ni `prompt` nativos.

#### Scenario: Confirmación de reemplazo de conteo

- **GIVEN** un operario que ya contó un artículo y envía nueva cantidad
- **WHEN** confirma la acción
- **THEN** la confirmación usa modal Synap, no diálogo nativo del navegador

---

### Requirement: Operación online y delegación offline

Con conectividad, el conteo SHOULD persistirse en servidor de inmediato. Sin conectividad, MUST delegarse a la cola offline (capability `stock-inventario-fisico-sync-offline`) manteniendo la misma restricción de conteo ciego en UI local.

#### Scenario: Conteo online exitoso

- **GIVEN** red disponible y campaña En conteo
- **WHEN** el operario registra cantidad
- **THEN** el servidor acepta el conteo y la UI muestra estado sincronizado

#### Scenario: Conteo offline encolado

- **GIVEN** sin conectividad y catálogo prefetched en IndexedDB
- **WHEN** el operario registra cantidad
- **THEN** el evento queda en cola local, la UI muestra pendiente de sync y MUST NOT mostrar saldo
