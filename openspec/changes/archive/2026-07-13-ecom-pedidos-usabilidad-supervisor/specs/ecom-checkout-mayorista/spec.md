# Delta for ecom-checkout-mayorista

**Change:** `ecom-pedidos-usabilidad-supervisor`

## ADDED Requirements

### REQ-CHK-010 — CodViajante operativo en alta PED

Al confirmar checkout mayorista (PED), el sistema MUST persistir en `comp_ped.CodViajante` el **viajante efectivo** resuelto por el helper único (`cod_viajante_operativo` con fallback `id_vendedor_usr`). MUST NOT usar atributos obsoletos `user.cod_viajante` / `codViajante` si difieren de `id_vendedor_usr`.

#### Scenario: Vendedor directo confirma pedido

- **GIVEN** vendedor con `id_vendedor_usr=42` y `cod_viajante_operativo=42`
- **WHEN** confirma PED
- **THEN** `comp_ped.CodViajante` MUST ser `42`

#### Scenario: Supervisor confirma en nombre de vendedor

- **GIVEN** supervisor con `cod_viajante_operativo=21`
- **WHEN** confirma PED
- **THEN** `comp_ped.CodViajante` MUST ser `21`, no el `id_vendedor_usr` del supervisor

---

### REQ-CHK-011 — Fix resolución sesión CodViajante

La función `_session_cod_viajante` (y equivalentes) MUST leer `id_vendedor_usr` de la sesión mayoristapp como fuente primaria de `CodViajante`, alineada con `cod_viajante_desde_sesion_usuario`. MUST integrar viajante operativo cuando esté definido.

#### Scenario: Sesión solo con id_vendedor_usr

- **GIVEN** sesión con `id_vendedor_usr=55` sin campos legacy `cod_viajante`
- **WHEN** checkout resuelve CodViajante
- **THEN** MUST devolver `55`, no null

#### Scenario: Bug legacy corregido

- **GIVEN** sesión donde antes `_session_cod_viajante` devolvía null
- **WHEN** confirma PED tras el fix
- **THEN** `comp_ped.CodViajante` MUST NOT quedar null si el usuario tiene viajante válido

---

### REQ-CHK-012 — CodViajante operativo en lote masivo

La confirmación batch masiva (`REQ-CHK-MAS-01`) MUST usar el mismo viajante efectivo que checkout simple para todos los PED del lote.

#### Scenario: Lote masivo con supervisor operativo

- **GIVEN** supervisor operando como vendedor 21 confirma lote de 3 sucursales
- **WHEN** se crean los 3 PED
- **THEN** los tres MUST tener `CodViajante=21`
