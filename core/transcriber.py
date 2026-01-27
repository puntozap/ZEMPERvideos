import os
import threading
import whisper

# Carga perezosa de modelos
_models = {}
_lock = threading.Lock()

def _get_model(model_size: str = "small"):
    with _lock:
        if model_size not in _models:
            _models[model_size] = whisper.load_model(model_size)
        return _models[model_size]

def transcribir(
    audio_path: str,
    idioma: str = "es",
    model_size: str = "small",
    temperature: float | None = None,
    beam_size: int | None = None
) -> str:
    """
    Transcribe un archivo de audio a texto en un idioma dado.
    Forzado a FP32 en CPU.
    """
    model = _get_model(model_size)
    kwargs = {"fp16": False}
    if idioma:
        kwargs["language"] = idioma
    if temperature is not None:
        kwargs["temperature"] = float(temperature)
    if beam_size is not None:
        kwargs["beam_size"] = int(beam_size)
    result = model.transcribe(audio_path, **kwargs)
    return result.get("text", "").strip()

def transcribir_srt(
    audio_path: str,
    out_dir: str,
    idioma: str = "es",
    model_size: str = "base",
    temperature: float | None = None,
    beam_size: int | None = None
) -> str:
    """
    Genera un archivo .srt para un audio y devuelve la ruta.
    """
    os.makedirs(out_dir, exist_ok=True)
    model = _get_model(model_size)
    kwargs = {"fp16": False}
    if idioma:
        kwargs["language"] = idioma
    if temperature is not None:
        kwargs["temperature"] = float(temperature)
    if beam_size is not None:
        kwargs["beam_size"] = int(beam_size)
    result = model.transcribe(audio_path, **kwargs)
    writer = whisper.utils.get_writer("srt", out_dir)
    writer(result, audio_path)
    base = os.path.splitext(os.path.basename(audio_path))[0]
    return os.path.join(out_dir, f"{base}.srt")
