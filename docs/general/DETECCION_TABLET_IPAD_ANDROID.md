# Detección de tablet (iPad / Android) para layout móvil

## Problema

El umbral de viewport (p. ej. ≤ 1366 px) **no es suficiente** para mostrar la versión móvil en tablets:

- **iPad (iPadOS 13+):** Safari y Chrome envían un User-Agent de **escritorio** (`Macintosh; Intel Mac OS X...`) idéntico a macOS, sin la cadena "iPad". El viewport en landscape puede ser > 1366 px (iPad Pro 12.9") o en pantallas de 10" el ancho típico ronda 1024–1180 px; según orientación y modelo, la cookie por viewport puede quedar en "desktop".
- **Android tablet:** En tablets "premium" (10"+), Chrome puede usar **User-Agent de escritorio** por defecto (desktop mode). Además, la distinción clásica por UA (teléfono = "Mobile" en UA, tablet = sin "Mobile") no es fiable: algunos fabricantes incluyen "Mobile" en tablets.

Por tanto, hace falta **detección específica de tablet** además del ancho de viewport.

---

## Documentación de referencia

### iPad / iPadOS 13+

- **Apple Developer Forums – User Agent in Safari on iPadOS**  
  https://developer.apple.com/forums/thread/119186  
  En iPadOS, Safari envía UA de escritorio (`Macintosh; Intel Mac OS X 10_15` + `AppleWebKit/605.1.15` + `Version/13.0` + `Safari/605.1.15`). No es posible distinguir iPad de macOS solo con el User-Agent en el servidor.

- **ScientiaMobile – Detect iPadOS 13**  
  https://scientiamobile.com/detect-ipados-13/  
  Explica que el análisis de User-Agent solo no permite identificar iPad; recomiendan detección por JavaScript/cloud (p. ej. WURFL.js).

- **Stack Overflow – How to detect iPad and iPad OS version in iOS 13 and Up?**  
  https://stackoverflow.com/questions/57765958/how-to-detect-ipad-and-ipad-os-version-in-ios-13-and-up  
  Heurística recomendada en cliente:
  ```javascript
  const isIPad = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;
  ```
  En Mac sin pantalla táctil `maxTouchPoints` es 0; en iPad suele ser 10. Así se distingue iPad (iPadOS 13+) de un Mac real.

- **MDN – Navigator.maxTouchPoints**  
  https://developer.mozilla.org/en-US/docs/Web/API/Navigator/maxTouchPoints  
  Soporte amplio en navegadores. Se puede usar para enviar al servidor (cookie, header, etc.) que el dispositivo se considera tablet/móvil.

### Android tablet

- **Stack Overflow – How do detect Android Tablets in general. Useragent?**  
  https://stackoverflow.com/questions/5341637/how-do-detect-android-tablets-in-general-useragent  

- **Webmasters – Detecting Android tablets vs phones with User Agent**  
  Regla habitual: en UA, **teléfono** suele llevar "Mobile"; **tablet** a menudo no. No es fiable al 100% (fabricantes y modos especiales).

- **Chrome for Developers – Desktop mode on premium tablets**  
  https://developer.chrome.com/blog/desktop-mode  
  En tablets Android "premium" (p. ej. 10"+), Chrome puede usar por defecto User-Agent de escritorio. La detección solo por UA en servidor no basta.

Conclusión: en Android tablet también conviene combinar UA (cuando indique móvil/tablet) con **viewport** y, si se puede, **detección en cliente** (p. ej. touch, resolución) y enviar resultado al servidor (cookie).

### Client Hints (HTTP)

- **MDN – Sec-CH-Viewport-Width, Client Hints**  
  https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-CH-Viewport-Width  
  El servidor puede pedir `Sec-CH-Viewport-Width` (y otros hints). Útil cuando el navegador los envía; **Safari tiene soporte limitado**, por lo que no puede ser la única base para iPad.

- **Sec-CH-UA-Mobile, Sec-CH-UA-Form-Factors**  
  Indican si el dispositivo se considera móvil o tablet. Misma limitación en Safari.

---

## Enfoque implementado en Synap: detección en dos capas

**Capa 1 — Servidor:** Cookie `device_hint` (mobile|desktop); si no hay, PHONE_PATTERNS y TABLET_PATTERNS en UA. iPad con UA Mac no detectable en servidor. **Capa 2 — Cliente:** Script detecta iPad (MacIntel + maxTouchPoints), Android tablet (Android sin Mobile), pantalla &lt; 768 px; setea `device_hint` y recarga. Compatibilidad: cookie `synap_prefer_mobile` (1/0). Endpoint opcional: POST `/set-device-hint/`.

---

## Enfoque recomendado para Synap (referencia)

Combinar **tres señales** (sin depender de servicios externos):

1. **User-Agent en servidor**  
   Mantener la lógica actual: si el UA contiene "iPad", "iPhone", "Android", "Mobile", etc., marcar `request.is_mobile = True`.

2. **Cookie por viewport (ya implementada)**  
   Script en cliente que, si el ancho de viewport es ≤ umbral (p. ej. 1366 px), setea `synap_prefer_mobile=1`. El middleware respeta esta cookie. Cubre ventanas estrechas y algunos casos de tablet en portrait.

3. **Detección de tablet en cliente y cookie**  
   En el mismo script que setea la cookie de viewport:
   - **iPad (iPadOS 13+):** si `navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1`, considerar dispositivo como tablet y forzar layout móvil (p. ej. setear `synap_prefer_mobile=1` aunque el viewport sea grande).
   - **Android tablet:** si el UA en cliente contiene "Android" y no "Mobile", o si se quiere ser más agresivo, considerar viewport mediano (p. ej. &lt; 1280) como tablet; en Synap ya se usa la cookie de viewport, que ayuda cuando el usuario tiene la ventana estrecha. Opcional: en cliente no hay un indicador tan claro como `maxTouchPoints` para “solo tablet Android”; se puede dejar que viewport + UA cubran la mayoría de casos.

Así, **iPad de 10" en landscape** que envía UA de escritorio y viewport &gt; 1366 seguiría mostrando desktop solo con (2). Añadiendo (3) y detectando iPad con `MacIntel` + `maxTouchPoints > 1`, se setea la cookie a móvil y se sirve la versión móvil aunque el ancho sea grande.

---

## Implementación sugerida (script en base_app.html)

En el script que ya gestiona la cookie `synap_prefer_mobile`:

1. **Detectar iPad (iPadOS 13+) en cliente:**  
   `var isIPad = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;`

2. **Decisión:**  
   - Si `isIPad === true`, forzar `preferMobile = '1'` (layout móvil), independientemente del ancho.  
   - Si no, mantener la lógica actual: `preferMobile = (w <= viewportMax) ? '1' : '0'`.

3. **Cookie y recarga:**  
   Si el valor de la cookie debe cambiar (por iPad o por viewport), setear la cookie y recargar cuando corresponda (igual que ahora).

Con esto, un iPad de 10" con Chrome o Safari que envía UA de escritorio y viewport grande dejará de verse como desktop.

---

## Resumen de referencias

| Tema | Fuente | Conclusión |
|------|--------|------------|
| iPad iPadOS 13 UA | Apple Developer Forums, ScientiaMobile | UA = Macintosh; imposible distinguir iPad de Mac solo en servidor. |
| Detección iPad en JS | Stack Overflow, Sentry issue | `navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1` → iPad. |
| Android tablet UA | Stack Overflow, Chrome blog | "Mobile" en UA ≈ phone; sin "Mobile" ≈ tablet; no fiable; Chrome en tablets premium usa desktop UA. |
| Client Hints | MDN | Sec-CH-Viewport-Width y form factor; Safari con soporte limitado. |
| Envío al servidor | Uso de cookie | Cliente setea cookie (p. ej. `synap_prefer_mobile`) según viewport y/o detección de tablet; middleware lee la cookie. |

---

## Criterios de aceptación

- En **iPad 10"** (Safari o Chrome, con UA de escritorio), la aplicación muestra la **versión móvil** (menú hamburguesa, layout en columna, etc.).
- En **Mac** con Safari/Chrome, se sigue mostrando la versión **desktop** (no se activa móvil por `maxTouchPoints` en futuros Mac con touch si se añaden; hoy los Mac sin touch tienen `maxTouchPoints === 0`).
- La detección no depende de servicios externos (WURFL, etc.); solo UA en servidor + script en cliente + cookie.
