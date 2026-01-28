import os
import re
import requests
from dotenv import load_dotenv

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

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
        "RESUMEN:\n...\nDESCRIPCION:\n...\nHASHTAGS:\n#...\n"
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

    resumen = ""
    descripcion = ""
    hashtags = ""
    current = None
    for line in content.splitlines():
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
        if current == "resumen":
            resumen = (resumen + " " + line).strip()
        elif current == "descripcion":
            descripcion = (descripcion + " " + line).strip()
        elif current == "hashtags":
            hashtags = (hashtags + " " + line).strip()

    return {"resumen": resumen, "descripcion": descripcion, "hashtags": hashtags}
