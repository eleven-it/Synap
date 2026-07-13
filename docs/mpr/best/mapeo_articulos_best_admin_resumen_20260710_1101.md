# Reporte de mapeo BEST → AdministraNET (artículos)

**Fecha:** 10/07/2026 11:01
**Modo:** solo lectura (sin cambios en DBs)
**Alcance BEST:** SKUs distintos en pedidos abiertos (`REP_ORDENES_COMBINADO`, Finalizada=0, Pendiente>0)
**Alcance AdministraNET:** `administranet1.articulo`
**Total SKUs BEST a mapear:** 257

## Resultado

| Estado | Cantidad | % |
|--------|----------|---|
| `MATCH_ALTO` | 131 | 51.0% |
| `MATCH_MEDIO` | 5 | 1.9% |
| `MATCH_BAJO` | 4 | 1.6% |
| `AMBIGUO` | 46 | 17.9% |
| `CONFLICTO_1_A_N` | 13 | 5.1% |
| `SIN_MATCH_CONFIABLE` | 2 | 0.8% |
| `SIN_CANDIDATO` | 56 | 21.8% |

**Match usable (ALTO+MEDIO sin conflicto):** 136 / 257 (52.9%)

- Detalle: `mapeo_articulos_best_admin_20260710_1101.csv`

## Estrategia de inferencia (capas)

| Capa | Señal | Peso / efecto |
|------|-------|---------------|
| A | `id_manual` = BEST `Id Articulo` (MMID) | score 100 (exacto) |
| B | Modelo numérico BEST (`Codigo`/`MMID`) ∈ `id_manual` o prefijo `NombreArticulo` | +40 base |
| C | Talle BEST vs T4/T5/TL/TM/`CodArtProv` T110/T120 | +25 / −10 |
| C | Colores BEST (MMID/MYL) vs tokens Blanco/Negro/BL/NE… | +10 por overlap (máx 3) +5 color primario |
| C | Pack (2P/3P) y marca en nombre | +5 c/u |
| D | Jaccard tokens descripción BEST vs `NombreArticulo` | hasta +20 |
| V | Dos BEST → mismo `IDArt` en ALTO/MEDIO | `CONFLICTO_1_A_N` |

**Umbrales:** ALTO ≥90; MEDIO ≥70; BAJO ≥50; AMBIGUO si 2.º candidato a ≤5 pts del 1.º (≥50); resto SIN_MATCH / SIN_CANDIDATO.

## Hallazgos bloqueantes

1. **Capa A = 0 hits** en pedidos abiertos: los códigos BEST (`AT2400BLBL4`) no están en `id_manual` (quedó el modelo corto `2400`, o códigos Puma tipo `906978`).
2. `id_manual` en AdministraNET **no identifica variante 1:1** (varios `IDArt` comparten el mismo modelo).
3. BEST **no tiene códigos de barra**; no hay puente EAN.
4. Hipótesis TL≈4 / TM≈5 es heurística: requiere confirmación de negocio.

## Cómo usar el reporte

1. Aceptar filas `MATCH_ALTO` / `MATCH_MEDIO` tras spot-check.
2. Resolver a mano `AMBIGUO`, `MATCH_BAJO`, `CONFLICTO_1_A_N`, `SIN_*`.
3. Congelar CSV final `best_id_articulo,IDArt` como fuente de verdad del cutover.
4. Opcional: repetir sobre catálogo completo `MM` (6501), no solo pedidos abiertos.

## Muestras

### MATCH_ALTO (131)
- BEST `AT2400BLBL4` «Atomik 2400 Medias Stripe x2 Bl/Bl 4» → Admin `1343` `2400` «2400 TL Atomik Media Stripe Blanco 2P» | score=95 | B_model+talle+color_overlap_1+color0+pack+marca
- BEST `AT2400BLBL5` «Atomik 2400 Medias Stripe x2 Bl/Bl 5» → Admin `1344` `2400` «2400 TM Atomik Media Stripe Blanco 2P» | score=95 | B_model+talle+color_overlap_1+color0+pack+marca
- BEST `AT2400NENE4` «Atomik 2400 Medias Stripe x2 Ne/Ne 4» → Admin `1345` `2400` «2400 TL Atomik Media Stripe Negro 2P» | score=95 | B_model+talle+color_overlap_1+color0+pack+marca
- BEST `AT2401BLBL4` «Atomik 2401(Atk-Caña)Media Liso x2 Bl/Bl 4» → Admin `128` `2401` «2401 TL Atomik Media Liso Blanco 2P» | score=96 | B_model+talle+color_overlap_1+color0+pack+marca
- BEST `AT2401BLBL5` «Atomik 2401(Atk-Caña)Media Liso x2 Bl/Bl 5» → Admin `126` `2401` «2401 TM Atomik Media Liso Blanco 2P» | score=96 | B_model+talle+color_overlap_1+color0+pack+marca

### MATCH_MEDIO (5)
- BEST `PU6512BLGRNE5` «PUMA 2576-01 Unisex Sneakers Half Terry 3P Bl/Gr/Ne 5» → Admin `817` `6512` «2576 Puma Sneakers Half Terry 1P Blanco Logo Negro» | score=76 | B_model+color_overlap_2+color0+marca
- BEST `PU7964MNBL3` «Puma 7964-03 CLYDE JUNIOR Q Mn/Bl 3» → Admin `644` `907964` «907964-03 Puma Clyde Junior Quarter Mn/Bl 2P» | score=75 | B_model+talle_diff+color_overlap_2+color0+pack+marca+jaccard_0.50
- BEST `PU7964RSBL3` «Puma 7964-04 CLYDE JUNIOR Q Rs/Bl 3» → Admin `646` `907964` «907964-04 Puma Clyde Junior Quarter Rs/Bl 2P» | score=75 | B_model+talle_diff+color_overlap_2+color0+pack+marca+jaccard_0.50
- BEST `VA510MNMN4` «Varios 510 SOX Bipacks LISA Mn/Mn 4» → Admin `266` `510` «510-05 T4 BS Medias Antideslizante Marino 2P» | score=86 | B_model+talle+color_overlap_1+color0+pack
- BEST `VA510MNMN5` «Varios 510 SOX Bipacks LISA Mn/Mn 5» → Admin `271` `510` «510-05 T5 BS Medias Antideslizante Marino 2P» | score=86 | B_model+talle+color_overlap_1+color0+pack

### MATCH_BAJO (4)
- BEST `PU4491BLBLBL3` «Puma 7958-02 Sport Junior T:4 3P Bl/Bl/Bl 3» → Admin `213` `907958` «907958-02 T4 Puma Sport Junior Blanco 3P» | score=62 | B_model+talle_diff+color_overlap_1+color0+pack+marca+jaccard_0.38
- BEST `PU4491NENENE3` «Puma 7958-01 Sport Junior T:4 3P Ne/Ne/Ne 3» → Admin `215` `907958` «907958-01 T4 Puma Sport Junior Negro 3P» | score=62 | B_model+talle_diff+color_overlap_1+color0+pack+marca+jaccard_0.38
- BEST `PU6512FUGRBL5` «Puma 2576-02 Unisex Sneakers Half Terry 3P Fu/Gr/Bl 5» → Admin `817` `6512` «2576 Puma Sneakers Half Terry 1P Blanco Logo Negro» | score=61 | B_model+color_overlap_1+marca
- BEST `PU7964NENE3` «Puma 7964-01 CLYDE JUNIOR Q Ne/Ne 3» → Admin `645` `907964` «907964-01 Puma Clyde Junior Quarter Negro 2P» | score=61 | B_model+talle_diff+color_overlap_1+color0+pack+marca

### AMBIGUO (46)
- BEST `AT2400BLNE4` «Atomik 2400 Medias Stripe x2 Bl/Ne 4» → Admin `1351` `2400` «2400 T4  Atomik Media Stripe Blanco Logo Negro 1Par» | score=99 | B_model+talle+color_overlap_2+color0+marca
- BEST `AT2400BLNE5` «Atomik 2400 Medias Stripe x2 Bl/Ne 5» → Admin `1349` `2400` «2400 T5  Atomik Media Stripe Blanco Logo Negro 1Par» | score=99 | B_model+talle+color_overlap_2+color0+marca
- BEST `AT2400NENE5` «Atomik 2400 Medias Stripe x2 Ne/Ne 5» → Admin `1346` `2400` «2400 TM Atomik Media Stripe Negro 2P» | score=95 | B_model+talle+color_overlap_1+color0+pack+marca
- BEST `AT2402BLGMNE4` «Atomik 2402(Atk-1025)Soquete Unisex Basico x3 Bl/Gm/Ne » → Admin `1318` `2402` «2402 T4 Atomik Soquete Unisex Basico Blanco Logo Negro » | score=100 | B_model+talle+color_overlap_2+color0+marca
- BEST `AT2402BLGMNE5` «Atomik 2402(Atk-1025)Soquete Unisex Basico x3 Bl/Gm/Ne » → Admin `1321` `2402` «2402 T5 Atomik Soquete Unisex Basico Blanco Logo Negro » | score=100 | B_model+talle+color_overlap_2+color0+marca

### CONFLICTO_1_A_N (13)
- BEST `LE7864AEBL5` «Levis 7864-M005 Reg Cut Sport Stripe 2P Ae/Bl 5» → Admin `1119` `` «7864 T5 Levis Reg Cut Sport Stripe Blanco Logo Rojo 1Pa» | score=87 | B_model+talle+color_overlap_1+marca+jaccard_0.38+conflicto_IDArt
- BEST `LE7864BLNE5` «Levis 7864-M001 Reg Cut Sport Stripe 2P Bl/Ne 5» → Admin `1119` `` «7864 T5 Levis Reg Cut Sport Stripe Blanco Logo Rojo 1Pa» | score=92 | B_model+talle+color_overlap_1+color0+marca+jaccard_0.38+conflicto_IDArt
- BEST `PU1025BLBLFU4` «Puma 0966-05 Inv. Sneaker 3P Bl/Bl/Fu 4» → Admin `1053` `1025` «8624 T4 Unisex Sneaker Plain Blanco Logo Verde 1Par» | score=81 | B_model+talle+color_overlap_1+color0+conflicto_IDArt
- BEST `PU1025BLM4NE4` «Puma 0966-07 Inv. Sneaker 3P Bl/M4/Ne 4» → Admin `1053` `1025` «8624 T4 Unisex Sneaker Plain Blanco Logo Verde 1Par» | score=81 | B_model+talle+color_overlap_1+color0+conflicto_IDArt
- BEST `PU1315AZCE3` «Puma 3340-16 Kids inv. Sneakers 2P Az/Ce 3» → Admin `42` `1315` «892570-04 T3 Puma Kids invisible Sneakers Negro 2P» | score=80 | B_model+talle+pack+marca+conflicto_IDArt

### SIN_MATCH_CONFIABLE (2)
- BEST `SEVA508BLNE4` «Varios 508 Futbol BS Blanco/Negro 4» → Admin `250` `508` «508-05 T5 BS Medias Futbol Rojo 1Par» | score=35 | B_model+talle_diff
- BEST `SEVA508NEBL4` «Varios 508 Futbol BS Negro/Blanco 4» → Admin `250` `508` «508-05 T5 BS Medias Futbol Rojo 1Par» | score=35 | B_model+talle_diff

### SIN_CANDIDATO (56)
- BEST `LE3953CRCR4` «Levis 3953-W004 Low Cut Sport 2P Cr/Cr 4» → Admin `` `` «» | score= | 
- BEST `LE3953MNMN4` «Levis 3953-W003 Low Cut Sport 2P Mn/Mn 4» → Admin `` `` «» | score= | 
- BEST `LE7862GTM45` «Levis (7862)7864-M004 Reg Cut Wordmark Logo 2P Gt/M4 5» → Admin `` `` «» | score= | 
- BEST `LE7862NENE5` «Levis (7862)7864-M006 Reg Cut Wordmark Logo 2P Ne/Ne 5» → Admin `` `` «» | score= | 
- BEST `LE7870CRCR4` «Levis 7870-W004 Short Cut Logo Sport 2P Cr/Cr 4» → Admin `` `` «» | score= | 
