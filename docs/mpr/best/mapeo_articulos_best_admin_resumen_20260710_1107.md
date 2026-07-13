# Reporte mapeo BEST → AdministraNET (v3)

**Fecha:** 10/07/2026 11:07
**Diccionario:** `diccionario_mapeo_articulos_best_admin_20260710_1107.md`
**Total SKUs pedidos abiertos:** 256

| Estado | v3 | v2 | v1 |
|--------|----|----|----|
| `MATCH_ALTO` | 168 | 162 | 131 |
| `MATCH_MEDIO` | 3 | 7 | 5 |
| `MATCH_BAJO` | 6 | 3 | 4 |
| `AMBIGUO` | 9 | 10 | 46 |
| `CONFLICTO_1_A_N` | 0 | 0 | 13 |
| `SIN_MATCH_CONFIABLE` | 25 | 23 | 2 |
| `SIN_CANDIDATO` | 45 | 51 | 56 |

**Usable v3 (ALTO+MEDIO):** **171/256 (66.8%)**

- Detalle: `mapeo_articulos_best_admin_20260710_1107.csv`
- Equivalencias usables (listas para cutover): `equivalencia_best_idart_usable_20260710_1107.csv`

## Impacto en migración MPR
Con el CSV usable se puede sembrar **171** SKUs de demanda abierta sin mapeo manual.
Quedan **85** SKUs en cola de revisión (`AMBIGUO`/`SIN_*`/`BAJO`/`CONFLICTO`).

## Muestras
### MATCH_ALTO (168)
- `AT2400BLBL4` [BL/BL|t4|p2] → `1343` «2400 TL Atomik Media Stripe Blanco 2P» score=124
- `AT2400BLBL5` [BL/BL|t5|p2] → `1344` «2400 TM Atomik Media Stripe Blanco 2P» score=124
- `AT2400BLNE4` [BL/NE|t4|p2] → `1347` «2400 TL Atomik Media Stripe Mix 2P» score=123
- `AT2400BLNE5` [BL/NE|t5|p2] → `1348` «2400 TM Atomik Media Stripe Mix 2P» score=123
- `AT2400NENE4` [NE/NE|t4|p2] → `1345` «2400 TL Atomik Media Stripe Negro 2P» score=124

### MATCH_MEDIO (3)
- `PU7964MNBL3` [MN/BL|t3|p2] → `644` «907964-03 Puma Clyde Junior Quarter Mn/Bl 2P» score=83
- `PU7964RSBL3` [RS/BL|t3|p2] → `646` «907964-04 Puma Clyde Junior Quarter Rs/Bl 2P» score=83
- `PU8022NEGMBL6` [NE/GM/BL|t6|p3] → `661` «888022-02 T6 Puma Sport  XXL Ne/Gm/Bl 3P» score=87

### AMBIGUO (9)
- `KP610BLBLBL6` [BL/BL/BL|t6|p3] → `340` «610 T4 Kamp Tripack  Bl/Gm/Ne 3P» score=81
- `KP610NENENE6` [NE/NE/NE|t6|p3] → `342` «610 T4 Kamp Tripack Negro 3P» score=80
- `PU1025AOAEMN5` [AO/AE/MN|t5|p3] → `33` «906807-16 T5 Puma Invisible Sneaker Ao/Ae/Mn 3P» score=87
- `PU6512BLGRNE5` [BL/GR/NE|t5|p3] → `816` «2576 T5 Puma Sneakers Half Terry Blanco Logo Negro» score=55
- `PU7374BLBLBL2` [BL/BL/BL|t2|p3] → `498` «907374-05 T2 Puma Kids Invisibles Blanco 3P» score=113

### SIN_CANDIDATO (45)
- `LE3953CRCR4` [CR/CR|t4|p2] → `` «» score=
- `LE3953MNMN4` [MN/MN|t4|p2] → `` «» score=
- `LE7870CRCR4` [CR/CR|t4|p2] → `` «» score=
- `LE7870NENE4` [NE/NE|t4|p2] → `` «» score=
- `LE8459AEMN5` [AE/MN|t5|p2] → `` «» score=

### SIN_MATCH_CONFIABLE (25)
- `KP610BLGMNE6` [BL/GM/NE|t6|p3] → `340` «610 T4 Kamp Tripack  Bl/Gm/Ne 3P» score=54
- `LE7538BLNE5` [BL/NE|t5|p2] → `1105` «7538 T5 Levis Mid Cut Batwing Logo Negro Logo Rojo» score=51
- `LE7862NENE5` [NE/NE|t5|p2] → `1118` «7864 T5 Levis Reg Cut Wordmark Logo Marino Logo Ae» score=41
- `LE7864AEBL5` [AE/BL|t5|p2] → `1119` «7864 T5 Levis Reg Cut Sport Stripe Blanco Logo Roj» score=38
- `LE7864BLNE5` [BL/NE|t5|p2] → `1120` «7864 T5 Levis Reg Cut Wordmark Logo Negro Logo Gri» score=51

### MATCH_BAJO (6)
- `LE7862GTM45` [GT/M4|t5|p2] → `1121` «7864 T5 Levis Reg Cut Wordmark Logo M4 Logo Gtopo » score=55
- `PU1315AZCE3` [AZ|t3|p2] → `42` «892570-04 T3 Puma Kids invisible Sneakers Negro 2P» score=69
- `PU1315RSCH3` [RS|t3|p2] → `42` «892570-04 T3 Puma Kids invisible Sneakers Negro 2P» score=69
- `PU595GMM4NE5` [GM/M4/NE|t5|p3] → `815` «2574 T5 Puma Sport M4 Logo Negro 1Par» score=55
- `PU6512FUGRBL5` [FU/GR/BL|t5|p3] → `822` «2576 T5 Puma Sneakers Half Terry Fucsia Logo Blanc» score=55

### CONFLICTO_1_A_N (0)
_sin filas_
