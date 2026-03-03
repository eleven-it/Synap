"""
Construye ítems de conocimiento para RAG desde la carpeta docs/.
Usado por GET /core/api/support/conocimiento/ (Support).
- Chunking por encabezados Markdown (##) y por tamaño máximo.
- Sistema por carpeta: docs/administranet_vb6/ → administranet, resto → synap.
"""
from pathlib import Path
import re

# Límite por chunk para no superar el del embedding (ej. 8192)
MAX_CHUNK_CHARS = 6000
# Carpeta cuyo contenido se etiqueta como AdministraNET (VB6)
ADMINISTRANET_VB6_SUBDIR = "administranet_vb6"


def _chunk_by_headers_and_size(content: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """
    Divide el texto por ## (y ###). Si una sección supera max_chars, la subdivide por longitud.
    """
    if not (content or "").strip():
        return []
    chunks = []
    # Dividir por ## o ### al inicio de línea
    sections = re.split(r'\n(?=#{2,3}\s)', content.strip())
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= max_chars:
            chunks.append(section)
        else:
            # Subdividir por párrafos o por longitud
            parts = section.split("\n\n")
            current = ""
            for part in parts:
                if len(current) + len(part) + 2 <= max_chars:
                    current = f"{current}\n\n{part}".strip() if current else part
                else:
                    if current:
                        chunks.append(current)
                    if len(part) > max_chars:
                        # Cortar por longitud con solapamiento mínimo
                        start = 0
                        while start < len(part):
                            end = start + max_chars
                            chunk = part[start:end]
                            chunks.append(chunk)
                            start = end
                        current = ""
                    else:
                        current = part
            if current:
                chunks.append(current)
    return chunks


def _sistema_for_path(relative_path: str) -> str:
    """administranet si la ruta contiene administranet_vb6, sino synap."""
    return "administranet" if ADMINISTRANET_VB6_SUBDIR in relative_path.replace("\\", "/") else "synap"


def build_conocimiento_items_from_docs(docs_dir: Path) -> list[dict]:
    """
    Recorre docs_dir recursivamente, lee .md, genera chunks y devuelve items para RAG.
    Cada item: { "text", "source_id", "metadata": { "sistema", "file" } }.
    """
    items = []
    if not docs_dir.is_dir():
        return items
    # Recorrer todos los .md
    for path in sorted(docs_dir.rglob("*.md")):
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        try:
            rel = path.relative_to(docs_dir)
        except ValueError:
            rel = path.name
        relative_path = str(rel).replace("\\", "/")
        sistema = _sistema_for_path(relative_path)
        file_meta = f"docs/{relative_path}"
        chunks = _chunk_by_headers_and_size(raw)
        for i, text in enumerate(chunks):
            if not text.strip():
                continue
            source_id = f"{relative_path}#{i}" if len(chunks) > 1 else relative_path
            source_id = source_id[:64]  # límite en Support
            items.append({
                "text": text.strip(),
                "source_id": source_id,
                "metadata": {"sistema": sistema, "file": file_meta},
            })
    return items
