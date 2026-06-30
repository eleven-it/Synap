import fs from 'fs';
import path from 'path';
import type { Page } from '@playwright/test';
import { CAPTURAS } from '../playwright.config';

let paso = 0;

export function resetCapturas() {
  paso = 0;
  fs.mkdirSync(CAPTURAS, { recursive: true });
}

export async function capturar(
  page: Page,
  slug: string,
  titulo: string,
  notas?: string,
): Promise<{ archivo: string; titulo: string; notas?: string }> {
  paso += 1;
  const nombre = `${String(paso).padStart(2, '0')}-${slug}.png`;
  const archivo = path.join(CAPTURAS, nombre);
  await page.screenshot({ path: archivo, fullPage: true });
  return { archivo: `docs/mpr/e2e/capturas/${nombre}`, titulo, notas };
}

export type RegistroPaso = {
  paso: number;
  titulo: string;
  ruta: string;
  captura?: string;
  validacion?: string;
  notas?: string;
};

export class RegistroManual {
  private entradas: RegistroPaso[] = [];

  add(entry: Omit<RegistroPaso, 'paso'>) {
    this.entradas.push({ paso: this.entradas.length + 1, ...entry });
  }

  toMarkdown(): string {
    const lines = [
      '# Registro E2E — Flujo MPR demanda → OPT → OPP',
      '',
      `Generado: ${new Date().toLocaleString('es-AR')}`,
      '',
      '| Paso | Pantalla | Validación | Captura |',
      '|------|----------|------------|---------|',
    ];
    for (const e of this.entradas) {
      const cap = e.captura ? `[${path.basename(e.captura)}](${e.captura.replace('docs/mpr/e2e/capturas/', 'capturas/')})` : '—';
      lines.push(
        `| ${e.paso} | ${e.titulo} | ${e.validacion || '—'} | ${cap} |`,
      );
    }
    lines.push('', '## Detalle por paso', '');
    for (const e of this.entradas) {
      lines.push(`### ${e.paso}. ${e.titulo}`);
      lines.push(`- **Ruta:** \`${e.ruta}\``);
      if (e.validacion) lines.push(`- **Validación:** ${e.validacion}`);
      if (e.notas) lines.push(`- **Notas:** ${e.notas}`);
      if (e.captura) lines.push(`- **Captura:** \`${e.captura}\``);
      lines.push('');
    }
    return lines.join('\n');
  }

  guardar(rutaRel: string) {
    const dest = path.resolve(__dirname, '../../../../docs/mpr/e2e', path.basename(rutaRel));
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.writeFileSync(dest, this.toMarkdown(), 'utf-8');
    return dest;
  }
}
