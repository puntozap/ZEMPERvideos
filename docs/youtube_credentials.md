# Manejo de credenciales de YouTube

Este documento explica cómo usar el nuevo módulo `core.youtube_credentials` para leer, registrar y comprobar credenciales JSON (cliente + refresh token) dentro del proyecto.

## Estructura de carpetas

- `credentials/`: directorio controlado por el módulo; aquí se almacenan todos los JSON válidos.
- `credentials/.active_credentials`: archivo interno que apunta al nombre del archivo activo.
- `output/`: **no** debe usarse para guardar credenciales.

## Flujo recomendado

1. Coloca el JSON proporcionado por Google (con `client_id`, `client_secret`, `refresh_token` y `token_uri`) en cualquier lugar temporal.
2. Importa `register_credentials` y pásale la ruta. Ejemplo:

```python
from core.youtube_credentials import register_credentials

register_credentials("descargas/mis-credenciales.json")
```

El módulo copia el archivo dentro de `credentials/`, evita duplicados comparando hashes y marca el archivo registrado como activo.

Si no cuentas con `refresh_token`, puedes usar un helper OAuth:

```python
from core.youtube_oauth import build_oauth_url, exchange_code_for_tokens

url = build_oauth_url(
    client_id="TU_CLIENT_ID.apps.googleusercontent.com",
    redirect_uri="urn:ietf:wg:oauth:2.0:oob",
    scopes=[
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtube.force-ssl",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ],
)
print("Abre esta URL en tu navegador, autoriza y pega el código:")
print(url)

tokens = exchange_code_for_tokens(
    client_id="TU_CLIENT_ID.apps.googleusercontent.com",
    client_secret="TU_CLIENT_SECRET",
    code="EL_CODIGO_QUE_TE_DIO_GOOGLE",
    redirect_uri="urn:ietf:wg:oauth:2.0:oob",
)
print(tokens)
```

Esta respuesta incluye `refresh_token`, que debes agregar al JSON antes de registrarlo.

> **Nota:** el alcance `https://www.googleapis.com/auth/yt-analytics.readonly` se requiere para consultar las métricas (videos vs shorts). Si ya registraste una credencial anterior, vuelve a generar el `refresh_token` incluyendo ese scope.

La pestaña “YouTube” del escritorio ya incluye esta ayuda: pega tus claves, genera la URL, abre el navegador y pega el código que te da Google para intercambiarlo. El refresh token aparece en el cuadro emergente y puedes copiarlo directamente al JSON desde allí antes de registrarlo.

3. Para usar la credencial activa basta con cargarla:

```python
from core.youtube_credentials import load_active_credentials

creds = load_active_credentials()
```

`load_active_credentials` levanta la credencial activa y valida que tenga todos los campos necesarios. Si no hay ninguna activa, lanza `FileNotFoundError`.

4. Puedes listar las credenciales disponibles con `available_credentials()` o cambiar manualmente la activa usando `mark_active(path)`.

## Verificaciones automáticas

- Antes de marcar un archivo como activo, el módulo comprueba que tiene el bloque `installed` o `web` y que contiene `client_id`, `client_secret`, `token_uri` y `refresh_token`.
- Si el archivo no es válido, se ignora y se busca el siguiente válido.
- El `.active_credentials` se actualiza automáticamente al registrar nuevas credenciales o cuando se detecta un archivo válido en `credentials/`.

## Cuándo usarlo

Utiliza este módulo como punto de partida del endpoint de YouTube: las funciones de autenticación (refresh tokens, OAuth flow) deben leer `load_active_credentials()` para conocer `client_id` y `refresh_token` actualizados. Si un nuevo archivo aparece (aunque tenga otro nombre), solo regístralo para que quede activo.
