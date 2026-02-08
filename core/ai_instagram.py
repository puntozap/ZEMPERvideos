import os
import re
import requests
from dotenv import load_dotenv

from core.api_endpoints import get_primary_endpoint_url
from core.video_transcription import obtener_transcripcion_para_video

OPENAI_API_URL = get_primary_endpoint_url("OpenAI Chat")

load_dotenv()


def _extract_section(content: str, label: str) -> str:
    pattern = rf"^{label}:\s*(.*)$"
    lines = content.splitlines()
    current = None
    out = []
    for line in lines:
        if re.match(pattern, line):
            current = label
            value = re.sub(pattern, r"\\1", line).strip()
            if value:
                out.append(value)
            continue
        if current == label:
            if re.match(r"^[A-Z_]+:\s*", line):
                break
            if line.strip():
                out.append(line.strip())
    return " ".join(out).strip()


def generar_descripcion_instagram(
    video_path: str,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    idioma: str = "es",
    hashtags: int = 8,
    logs=None,
) -> dict:
    if api_key is None or not str(api_key).strip():
        api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("Falta API key de OpenAI. Agrega OPENAI_API_KEY en el .env.")

    texto = obtener_transcripcion_para_video(video_path, idioma=idioma, logs=logs)
    if not texto:
        raise RuntimeError("La transcripción no contiene texto útil.")

    max_chars = 8000
    if len(texto) > max_chars:
        if logs:
            logs(f"Texto truncado a {max_chars} caracteres para IA.")
        texto = texto[:max_chars]

    system = (
        "Eres un redactor para Instagram Reels. Responde SOLO en español y con el formato exacto:\n"
        "DESCRIPCION:\n...\nHASHTAGS:\n#...\nMENCIONES:\n@...\n\n"
        "Reglas:\n"
        f"- Genera una descripción breve, clara y atractiva.\n"
        f"- Usa exactamente {int(hashtags)} hashtags relevantes.\n"
        "- Si no hay menciones necesarias, deja MENCIONES vacío.\n"
    )
    user = f"Transcripción del video:\n{texto}"

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
        "temperature": 0.6,
    }
    if logs:
        logs("Llamando a OpenAI para generar descripción de Instagram...")
    resp = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=90)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI error {resp.status_code}: {resp.text[:300]}")
    content = resp.json()["choices"][0]["message"]["content"].strip()

    descripcion = _extract_section(content, "DESCRIPCION")
    hashtags_txt = _extract_section(content, "HASHTAGS")
    menciones = _extract_section(content, "MENCIONES")

    return {
        "descripcion": descripcion.strip(),
        "hashtags": hashtags_txt.strip(),
        "menciones": menciones.strip(),
        "raw": content,
    }
