import requests
import time
import os

from core.instagram_auth import exchange_long_lived_token, token_expired


class InstagramUploader:
    """
    Maneja la subida de Reels a Instagram mediante la Graph API.
    Referencia: docs/instagram_reel_upload.md
    """
    def __init__(
        self,
        access_token: str,
        instagram_account_id: str,
        version: str = "v19.0",
        app_id: str | None = None,
        app_secret: str | None = None,
        token_expires_at: int | None = None,
        on_token_update=None,
    ):
        self.access_token = access_token
        self.account_id = instagram_account_id
        self.base_url = f"https://graph.facebook.com/{version}"
        self.app_id = app_id
        self.app_secret = app_secret
        self.token_expires_at = token_expires_at
        self.on_token_update = on_token_update

    def _ensure_token(self, log_fn=None):
        if not token_expired(self.token_expires_at):
            return
        if not self.app_id or not self.app_secret:
            if log_fn:
                log_fn("⚠️ Token expirado y faltan App ID/Secret para renovarlo.")
            return
        if log_fn:
            log_fn("🔁 Renovando token de Instagram (long-lived)...")
        data = exchange_long_lived_token(
            short_lived_token=self.access_token,
            app_id=self.app_id,
            app_secret=self.app_secret,
            api_version=self.base_url.split("/")[-1],
        )
        self.access_token = data.get("access_token", self.access_token)
        self.token_expires_at = data.get("expires_at")
        if self.on_token_update:
            self.on_token_update(data)

    def upload_reel(self, video_url: str, caption: str = "", share_to_feed: bool = True, log_fn=print):
        """
        Orquesta el proceso de subida:
        1. Crea el contenedor de medios con la URL del video.
        2. Espera a que Instagram procese el video.
        3. Publica el contenedor.
        """
        self._ensure_token(log_fn=log_fn)
        if log_fn:
            log_fn("?? IG: Creando contenedor para el video...")
        container_id = self._create_media_container(video_url, caption, share_to_feed, log_fn)
        if not container_id:
            return None
        if log_fn:
            log_fn(f"? IG: Esperando procesamiento (ID: {container_id})...")
        if self._wait_for_processing(container_id, log_fn=log_fn):
            if log_fn:
                log_fn("?? IG: Publicando Reel...")
            media_id = self._publish_media(container_id, log_fn)
            if media_id and log_fn:
                log_fn(f"? IG: Reel publicado con ?xito (Media ID: {media_id})")
            return media_id
        if log_fn:
            log_fn("? IG: Error. El video no se proces? correctamente.")
        return None

    def upload_reel_resumable(self, file_path: str, caption: str = "", share_to_feed: bool = True, log_fn=print):
        """
        Sube un Reel usando carga resumible (rupload) sin depender de URLs p?blicas.
        Flujo:
        1) Crear contenedor con upload_type=resumable.
        2) Subir el archivo binario al endpoint rupload con offset/file_size.
        3) Esperar procesamiento.
        4) Publicar.
        """
        self._ensure_token(log_fn=log_fn)
        if log_fn:
            log_fn("?? IG: Creando contenedor resumible...")
        container_id, upload_uri = self._create_resumable_container(caption, share_to_feed, log_fn)
        if not container_id or not upload_uri:
            return None
        if log_fn:
            log_fn("?? IG: Subiendo archivo directamente a Instagram...")
        if not self._upload_resumable_file(upload_uri, file_path, log_fn):
            return None
        if log_fn:
            log_fn(f"? IG: Esperando procesamiento (ID: {container_id})...")
        if self._wait_for_processing(container_id, log_fn=log_fn):
            if log_fn:
                log_fn("?? IG: Publicando Reel...")
            media_id = self._publish_media(container_id, log_fn)
            if media_id and log_fn:
                log_fn(f"? IG: Reel publicado con ?xito (Media ID: {media_id})")
            return media_id
        if log_fn:
            log_fn("? IG: Error. El video no se proces? correctamente.")
        return None

    def _create_media_container(self, video_url, caption, share_to_feed, log_fn):
        url = f"{self.base_url}/{self.account_id}/media"
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": str(share_to_feed).lower(),
            "access_token": self.access_token
        }
        try:
            r = requests.post(url, data=payload)
            r.raise_for_status()
            return r.json().get("id")
        except Exception as e:
            self._log_error(e, "creando contenedor IG", log_fn)
            return None

    def _wait_for_processing(self, container_id, timeout=300, interval=10, log_fn=None):
        start_time = time.time()
        url = f"{self.base_url}/{container_id}"
        params = {
            "fields": "status_code,status",
            "access_token": self.access_token
        }
        
        while time.time() - start_time < timeout:
            try:
                r = requests.get(url, params=params)
                data = r.json()
                status = data.get("status_code")
                
                if status == "FINISHED":
                    return True
                elif status == "ERROR":
                    if log_fn: log_fn(f"❌ IG Estado Error: {data}")
                    return False
                elif status == "IN_PROGRESS":
                    time.sleep(interval)
                else:
                    time.sleep(interval)
            except Exception as e:
                if log_fn: log_fn(f"⚠️ Error verificando estado IG: {e}")
                time.sleep(interval)
        
        return False

    def _publish_media(self, container_id, log_fn):
        url = f"{self.base_url}/{self.account_id}/media_publish"
        payload = {
            "creation_id": container_id,
            "access_token": self.access_token
        }
        try:
            r = requests.post(url, data=payload)
            r.raise_for_status()
            return r.json().get("id")
        except Exception as e:
            self._log_error(e, "publicando IG", log_fn)
            return None

    def _create_resumable_container(self, caption: str, share_to_feed: bool, log_fn):
        url = f"{self.base_url}/{self.account_id}/media"
        payload = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "access_token": self.access_token,
        }
        # share_to_feed es opcional; sÃ³lo enviarlo si viene definido
        payload["share_to_feed"] = str(share_to_feed).lower()
        try:
            r = requests.post(url, data=payload)
            r.raise_for_status()
            data = r.json()
            upload_uri = data.get("uri") or data.get("upload_url") or data.get("upload_uri")
            if upload_uri and upload_uri.startswith("/"):
                upload_uri = f"https://rupload.facebook.com{upload_uri}"
            return data.get("id"), upload_uri
        except Exception as e:
            self._log_error(e, "creando contenedor resumible IG", log_fn)
            return None, None

    def _upload_resumable_file(self, upload_uri: str, file_path: str, log_fn):
        if not os.path.exists(file_path):
            if log_fn:
                log_fn(f"❌ Archivo no encontrado: {file_path}")
            return False
        file_size = os.path.getsize(file_path)
        headers = {
            "Authorization": f"OAuth {self.access_token}",
            "offset": "0",
            "file_size": str(file_size),
            "Content-Type": "application/octet-stream",
            "Content-Length": str(file_size),
        }
        try:
            with open(file_path, "rb") as f:
                payload = f.read()
            r = requests.post(upload_uri, headers=headers, data=payload)
            r.raise_for_status()
            return True
        except Exception as e:
            self._log_error(e, "subiendo archivo IG (resumable)", log_fn)
            if hasattr(e, "response") and e.response is not None and log_fn:
                preview = (e.response.text or "").strip()[:500]
                if preview:
                    log_fn(f"   Respuesta: {preview}")
            return False

    def _log_error(self, e, context, log_fn):
        if not log_fn:
            return
        msg = f"❌ Error {context}: {e}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                msg += f"\n   HTTP: {e.response.status_code}"
                detail = e.response.json()
                error_obj = detail.get('error', {})
                msg += f"\n   Tipo: {error_obj.get('type')}"
                msg += f"\n   Mensaje: {error_obj.get('message')}"
                if error_obj.get('code') is not None:
                    msg += f"\n   CÃ³digo: {error_obj.get('code')}"
                if error_obj.get('error_subcode') is not None:
                    msg += f"\n   SubcÃ³digo: {error_obj.get('error_subcode')}"
                if error_obj.get('error_user_title'):
                    msg += f"\n   Titulo usuario: {error_obj.get('error_user_title')}"
                if error_obj.get('error_user_msg'):
                    msg += f"\n   Msg usuario: {error_obj.get('error_user_msg')}"
            except Exception:
                msg += f"\n   Raw: {e.response.text}"
        log_fn(msg)
