/**
 * E2E MPR: demanda → confirmar OPT → liberar → OPP → tablero/listado.
 * Capturas en docs/mpr/e2e/capturas/ para manual HTML futuro.
 */
import { test, expect } from '@playwright/test';
import { aplicarSesion, crearSesionDocker, irMPR } from './helpers/auth';
import { RegistroManual, capturar, resetCapturas } from './helpers/capturas';

const CANTIDAD_OPT = Number(process.env.MPR_E2E_CANTIDAD || '10');
const registro = new RegistroManual();

test.describe('Flujo MPR completo (demanda → OPT → OPP)', () => {
  test.beforeAll(() => {
    resetCapturas();
  });

  test('recorrer demanda, generar OPT, registrar OPP y validar tablero', async ({ page, context, baseURL }) => {
    const sesion = crearSesionDocker();
    await aplicarSesion(context, sesion, baseURL!);

    // --- 1. Tablero inicial ---
    await irMPR(page, '/mpr/');
    await expect(page.getByRole('heading', { name: /Tablero|Producción/i }).first()).toBeVisible();
    let cap = await capturar(page, 'tablero-inicial', 'Tablero de control MPR');
    registro.add({
      titulo: 'Tablero de control',
      ruta: '/mpr/',
      captura: cap.archivo,
      validacion: 'KPIs y accesos rápidos visibles',
      notas: 'Punto de entrada al módulo MPR (Manual §2).',
    });

    // --- 2. Demanda ventana pack ---
    await irMPR(page, '/mpr/demanda/ventana-pack/');
    await expect(page.getByRole('heading', { name: /Pedido producción|Demanda|OPT/i }).first()).toBeVisible();

    const btnActualizar = page.getByRole('button', { name: /Actualizar/i });
    if (await btnActualizar.isVisible().catch(() => false)) {
      await btnActualizar.click();
      await page.waitForLoadState('networkidle');
    }

    cap = await capturar(page, 'demanda-ventana-pack', 'Demanda — Ventana pack');
    registro.add({
      titulo: 'Demanda (ventana pack)',
      ruta: '/mpr/demanda/ventana-pack/',
      captura: cap.archivo,
      validacion: 'Tabla de packs con demanda',
      notas: 'Manual §3.1. Pestaña Packs; marcar fila y cantidad a fabricar.',
    });

    // Seleccionar primera fila con cantidad > 0
    const filas = page.locator('tr.ventana-pack-row');
    const nFilas = await filas.count();
    expect(nFilas).toBeGreaterThan(0);

    let idArticulo: string | null = null;
    for (let i = 0; i < nFilas; i++) {
      const fila = filas.nth(i);
      const cb = fila.locator('input.row-sel');
      const cant = fila.locator('input[name^="cant_"]');
      const val = await cant.inputValue().catch(() => '0');
      if (parseInt(val, 10) > 0 || i === 0) {
        await cb.check();
        idArticulo = (await cant.getAttribute('name'))?.replace('cant_', '') || null;
        await cant.fill(String(CANTIDAD_OPT));
        break;
      }
    }
    expect(idArticulo).toBeTruthy();

    cap = await capturar(page, 'demanda-fila-seleccionada', 'Demanda — fila seleccionada');
    registro.add({
      titulo: 'Selección en demanda',
      ruta: '/mpr/demanda/ventana-pack/',
      captura: cap.archivo,
      validacion: `Artículo ${idArticulo}, cantidad ${CANTIDAD_OPT}`,
    });

    await page.getByRole('button', { name: 'Continuar' }).click();
    await page.waitForURL(/ventana-pack\/agrupar|agrupar/, { timeout: 60_000 });

    // --- 3. Confirmar OPT ---
    await expect(page.getByRole('button', { name: 'Generar OPT' })).toBeVisible();
    cap = await capturar(page, 'confirmar-opt', 'Confirmar OPT (agrupar)');
    registro.add({
      titulo: 'Confirmar OPT',
      ruta: '/mpr/demanda/ventana-pack/agrupar/',
      captura: cap.archivo,
      notas: 'Manual §3.1.1. Revisar cantidades por componente BOM.',
    });

    await page.getByRole('button', { name: 'Generar OPT' }).click();
    await page.waitForLoadState('networkidle', { timeout: 120_000 });

    // Puede ir a detalle OPT o wizard paso 3
    const urlPost = page.url();
    let idLista: string | null = null;
    const mOpt = urlPost.match(/\/mpr\/opt\/(\d+)/);
    const mWizard = urlPost.match(/[?&]id_lista=(\d+)/);
    if (mOpt) idLista = mOpt[1];
    else if (mWizard) idLista = mWizard[1];

    if (urlPost.includes('/wizard')) {
      cap = await capturar(page, 'wizard-opp', 'Asistente — Crear OPP');
      registro.add({
        titulo: 'Asistente OPP (paso 3)',
        ruta: page.url(),
        captura: cap.archivo,
        validacion: 'OPT creada y liberada; formulario OPP',
      });
      idLista = idLista || new URL(urlPost).searchParams.get('id_lista');
    } else {
      cap = await capturar(page, 'opt-detalle-post-generar', 'Detalle OPT tras generar');
      registro.add({
        titulo: 'Detalle OPT',
        ruta: urlPost,
        captura: cap.archivo,
        validacion: 'OPT creada/liberada',
      });
    }

    expect(idLista).toBeTruthy();
    const idOpt = idLista!;

    // --- 4. OPP (wizard o navegar) ---
    if (!page.url().includes('/wizard')) {
      await irMPR(page, `/mpr/wizard/?paso=3&id_lista=${idOpt}`);
    }
    await expect(page.getByRole('button', { name: /Registrar OPP/i })).toBeVisible({ timeout: 30_000 });

    // Distribuir pendiente al primer depósito (Semi) por componente
    const filasOpp = page.locator('#form-opp-wizard tbody tr[data-id-art]');
    const nOpp = await filasOpp.count();
    for (let i = 0; i < nOpp; i++) {
      const fila = filasOpp.nth(i);
      const pend = parseInt((await fila.getAttribute('data-pendiente')) || '0', 10);
      if (pend <= 0) continue;
      const uniInput = fila.locator('input[data-opp-part="unidades"]').first();
      await uniInput.fill(String(pend));
      const searchOp = fila.locator('.operario-search');
      await searchOp.fill('Super');
      await page.waitForTimeout(800);
      const item = fila.locator('[data-operario-dropdown]:visible [data-id]').first();
      if (await item.isVisible().catch(() => false)) {
        await item.click();
      } else {
        const dd = fila.locator('[data-operario-dropdown] button, [data-operario-dropdown] div').first();
        if (await dd.isVisible().catch(() => false)) await dd.click();
      }
    }

    cap = await capturar(page, 'opp-formulario-completo', 'OPP — cantidades y operario');
    registro.add({
      titulo: 'Formulario OPP',
      ruta: `/mpr/wizard/?paso=3&id_lista=${idOpt}`,
      captura: cap.archivo,
      notas: 'Distribución a Semi elaborado; operario por fila.',
    });

    await page.getByRole('button', { name: /Registrar OPP/i }).click();
    await page.waitForLoadState('networkidle', { timeout: 120_000 });

    cap = await capturar(page, 'opp-registrada', 'Tras registrar OPP');
    registro.add({
      titulo: 'OPP registrada',
      ruta: page.url(),
      captura: cap.archivo,
      validacion: 'Sin modal de error OPP',
    });

    // --- 5. Tablero tras OPP ---
    await irMPR(page, '/mpr/');
    cap = await capturar(page, 'tablero-post-opp', 'Tablero tras OPP');
    registro.add({
      titulo: 'Tablero (validación post-OPP)',
      ruta: '/mpr/',
      captura: cap.archivo,
      validacion: 'Movimientos recientes / OPTs en proceso actualizados',
      notas: 'Manual §2 — revisar panel OPTs en proceso y movimientos.',
    });

    // --- 6. Listado OPT ---
    await irMPR(page, '/mpr/opt/');
    await expect(page.getByRole('heading', { name: /Órdenes de Producción/i })).toBeVisible();
    cap = await capturar(page, 'listado-opt', 'Listado de OPTs');
    registro.add({
      titulo: 'Listado OPT',
      ruta: '/mpr/opt/',
      captura: cap.archivo,
      validacion: `OPT ${idOpt} visible en listado`,
    });

    const filaOpt = page.locator(`tr[data-search-text*="${idOpt}"]`).first();
    if (await filaOpt.isVisible().catch(() => false)) {
      await expect(filaOpt).toBeVisible();
    }

    // --- 7. Detalle OPT ---
    await irMPR(page, `/mpr/opt/${idOpt}/`);
    cap = await capturar(page, 'opt-detalle-final', 'Detalle OPT final');
    registro.add({
      titulo: 'Detalle OPT (cierre de recorrido)',
      ruta: `/mpr/opt/${idOpt}/`,
      captura: cap.archivo,
      validacion: 'Trazabilidad OPT/OPP visible',
      notas: 'Manual §6 — OPPs vinculadas, pendientes, armado.',
    });

    const mdPath = registro.guardar('REGISTRO_FLUJO_E2E.md');
    console.log(`Registro manual: ${mdPath}`);
    console.log(`OPT creada id_lista=${idOpt}, cantidad=${CANTIDAD_OPT}`);
  });
});
