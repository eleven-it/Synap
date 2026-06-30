import { execSync } from 'child_process';
import type { BrowserContext, Page } from '@playwright/test';

export interface SesionE2E {
  session_key: string;
  cookie_name: string;
  base_empresa: string;
  cod_usuario: string;
}

export function crearSesionDocker(
  codUsuario = process.env.SYNAP_COD_USUARIO || 'Supervisor',
  baseEmpresa = process.env.SYNAP_BASE_EMPRESA || 'administranet96',
): SesionE2E {
  const cmd =
    `docker exec Synap_app python manage.py crear_sesion_e2e ` +
    `--cod-usuario=${codUsuario} --base-empresa=${baseEmpresa} --json`;
  const raw = execSync(cmd, { encoding: 'utf-8' }).trim();
  const lastLine = raw.split('\n').filter((l) => l.startsWith('{')).pop() || raw;
  return JSON.parse(lastLine) as SesionE2E;
}

export async function aplicarSesion(context: BrowserContext, sesion: SesionE2E, baseURL: string) {
  const url = new URL(baseURL);
  await context.addCookies([
    {
      name: sesion.cookie_name,
      value: sesion.session_key,
      domain: url.hostname,
      path: '/',
      httpOnly: true,
      sameSite: 'Lax',
    },
  ]);
}

export async function irMPR(page: Page, ruta: string) {
  await page.goto(ruta.startsWith('/') ? ruta : `/${ruta}`, { waitUntil: 'networkidle' });
  if (page.url().includes('/login')) {
    throw new Error('Sesión inválida: redirigió a login.');
  }
}
