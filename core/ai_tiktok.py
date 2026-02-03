import os
import re
import json
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
from core.api_endpoints import get_primary_endpoint_url

OPENAI_API_URL = get_primary_endpoint_url("OpenAI Chat")

# Cargar variables desde .env si existe
load_dotenv()

def _extraer_texto_srt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()
    data = data.replace("\r\n", "\n")
    lines = []
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if "-->" in line:
            continue
        line = re.sub(r"\{\\.*?\}", "", line)
        lines.append(line)
    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _extraer_cues_srt(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read().replace("\r\n", "\n")
    blocks = data.split("\n\n")
    cues = []
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        if "-->" not in lines[1]:
            continue
        times = lines[1]
        text_lines = []
        for l in lines[2:]:
            l = re.sub(r"\{\\.*?\}", "", l)
            if l:
                text_lines.append(l)
        text = " ".join(text_lines).strip()
        if not text:
            continue
        cues.append({"time": times, "text": text})
    return cues

def generar_descripcion_tiktok(
    srt_path: str,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    logs=None
) -> dict:
    if api_key is None or not str(api_key).strip():
        api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("Falta API key de OpenAI. Agrega OPENAI_API_KEY en el .env.")

    texto = _extraer_texto_srt(srt_path)
    if not texto:
        raise RuntimeError("El SRT no contiene texto util.")

    max_chars = 8000
    if len(texto) > max_chars:
        if logs: logs(f"Texto truncado a {max_chars} caracteres para IA.")
        texto = texto[:max_chars]

    system = (
        "Eres un redactor para TikTok. Responde SOLO en español y con el formato exacto:\n"
        "TITULO:\n...\nRESUMEN:\n...\nDESCRIPCION:\n...\nHASHTAGS:\n#...\n"
        "El TITULO debe ser un clickbait durisimo (corto y muy llamativo). "
        "Incluye hashtags relevantes al tema, y SIEMPRE agrega #Venezuela y #Caracas."
    )
    user = f"Transcripcion (resumida):\n{texto}"

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "developer", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
    }
    if logs: logs("Llamando a OpenAI...")
    resp = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"].strip()

    titulo = ""
    resumen = ""
    descripcion = ""
    hashtags = ""
    current = None
    for line in content.splitlines():
        if line.startswith("TITULO:"):
            current = "titulo"
            titulo = line.replace("TITULO:", "").strip()
            continue
        if line.startswith("RESUMEN:"):
            current = "resumen"
            resumen = line.replace("RESUMEN:", "").strip()
            continue
        if line.startswith("DESCRIPCION:"):
            current = "descripcion"
            descripcion = line.replace("DESCRIPCION:", "").strip()
            continue
        if line.startswith("HASHTAGS:"):
            current = "hashtags"
            hashtags = line.replace("HASHTAGS:", "").strip()
            continue
        if current == "titulo":
            titulo = (titulo + " " + line).strip()
        elif current == "resumen":
            resumen = (resumen + " " + line).strip()
        elif current == "descripcion":
            descripcion = (descripcion + " " + line).strip()
        elif current == "hashtags":
            hashtags = (hashtags + " " + line).strip()

    return {"titulo": titulo, "resumen": resumen, "descripcion": descripcion, "hashtags": hashtags}


def generar_recomendaciones_clips(
    srt_path: str,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    logs=None
) -> dict:
    if api_key is None or not api_key.strip():
        api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("Falta API key de OpenAI. Agrega OPENAI_API_KEY en el .env.")

    cues = _extraer_cues_srt(srt_path)
    if not cues:
        raise RuntimeError("El SRT no contiene cues validos.")

    # Limitar contenido para no exceder tokens
    max_cues = 180
    if len(cues) > max_cues:
        cues = cues[:max_cues]
        if logs:
            logs(f"Cues truncados a {max_cues} para IA.")

    payload_text = "\n".join([f"{c['time']} | {c['text']}" for c in cues])
    max_chars = 12000
    if len(payload_text) > max_chars:
        payload_text = payload_text[:max_chars]
        if logs:
            logs(f"Texto truncado a {max_chars} caracteres para IA.")

    system = (
        "Actúa como un editor profesional de contenido viral para TikTok, "
        "enfocado en entrevistas, análisis y conversaciones largas.\n\n"
        "Voy a proporcionarte un archivo SRT con marcas de tiempo. "
        "Tu tarea es identificar BLOQUES NARRATIVOS ENTRELAZABLES "
        "con alto potencial de retención y viralidad.\n\n"
        "Cada bloque debe durar entre 25 y 50 segundos. "
        "Los bloques pueden SOLAPARSE en el tiempo "
        "y NO deben ser clips cerrados.\n\n"
        "Para cada bloque identificado, entrega EXACTAMENTE este formato:\n\n"
        "────────────────────────\n"
        "Bloque #X\n\n"
        "Rango de tiempo:\n"
        "mm:ss → mm:ss\n\n"
        "Duración aproximada:\n"
        "XX segundos\n\n"
        "Función narrativa del bloque:\n"
        "Indica si funciona principalmente como:\n"
        "- Gancho\n"
        "- Desarrollo\n"
        "- Escalada\n"
        "- Giro\n"
        "- Remate\n"
        "- Cliffhanger\n\n"
        "Por qué este bloque es fuerte:\n"
        "Explica por qué este fragmento mantiene la atención\n"
        "(idea completa, tensión progresiva, afirmación clara,\n"
        "confrontación, revelación, cambio de tono, etc.).\n\n"
        "Cómo se puede editar o reutilizar:\n"
        "Describe cómo este bloque permite:\n"
        "- cortar inicio o final sin perder sentido\n"
        "- empalmar con otros bloques\n"
        "- reutilizar el cierre como apertura de otro clip\n"
        "- dividir internamente si se necesita\n\n"
        "Bloques compatibles:\n"
        "Indica con qué otros bloques se puede entrelazar\n"
        "y en qué orden funciona mejor.\n\n"
        "────────────────────────\n\n"
        "Reglas editoriales:\n"
        "- Piensa exclusivamente en formato TikTok.\n"
        "- Prioriza ideas completas y comprensibles.\n"
        "- Evita microfragmentos.\n"
        "- Permite solapamiento entre bloques.\n"
        "- Diseña para control editorial en postproducción.\n"
        "- El objetivo es retención sostenida (no solo shock).\n"
    )
    user = f"SRT cues:\n{payload_text}"

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "developer", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
    }
    if logs:
        logs("Llamando a OpenAI para recomendaciones...")
    resp = None
    for attempt in range(3):
        try:
            resp = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=120)
            break
        except requests.exceptions.ReadTimeout:
            if logs:
                logs(f"Timeout en OpenAI (intento {attempt+1}/3). Reintentando...")
            time.sleep(1.5 * (attempt + 1))
        except Exception as e:
            if logs:
                logs(f"Error de red OpenAI: {e}")
            time.sleep(1.5 * (attempt + 1))
    if resp is None:
        raise RuntimeError("No se pudo contactar OpenAI tras varios intentos.")
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"].strip()
    def _to_hhmmss(ts_mmss: str) -> str:
        try:
            mm, ss = ts_mmss.strip().split(":")
            return f"00:{int(mm):02d}:{int(ss):02d},000"
        except Exception:
            return "00:00:00,000"

    blocks = []
    parts = content.split("Bloque #")
    for part in parts[1:]:
        block_num = part.splitlines()[0].strip()
        rango_match = re.search(r"Rango de tiempo:\s*\n\s*(\d{1,2}:\d{2})\s*→\s*(\d{1,2}:\d{2})", part)
        dur_match = re.search(r"Duración aproximada:\s*\n\s*([0-9]+)\s*segundos", part)
        func_match = re.search(r"Función narrativa del bloque:\s*\n([^\n]+)", part)
        why_match = re.search(r"Por qué este bloque es fuerte:\s*\n(.+?)\n\nCómo se puede editar o reutilizar:", part, re.S)
        how_match = re.search(r"Cómo se puede editar o reutilizar:\s*\n(.+?)\n\nBloques compatibles:", part, re.S)
        comp_match = re.search(r"Bloques compatibles:\s*\n(.+)", part, re.S)
        if not rango_match:
            continue
        start = _to_hhmmss(rango_match.group(1))
        end = _to_hhmmss(rango_match.group(2))
        blocks.append({
            "block": block_num,
            "start_time": start,
            "end_time": end,
            "duration_seconds": int(dur_match.group(1)) if dur_match else None,
            "narrative_function": (func_match.group(1).strip("- ").strip() if func_match else ""),
            "why": (why_match.group(1).strip() if why_match else ""),
            "how_edit": (how_match.group(1).strip() if how_match else ""),
            "compatible": (comp_match.group(1).strip() if comp_match else ""),
        })
    parsed = {"clips": blocks, "raw": content}

    out_dir = os.path.join("output", "ia")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(srt_path))[0]
    out_path = os.path.join(out_dir, f"{base}_clips_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    text_out = content

    return {"data": parsed, "json_path": out_path, "text": text_out}
