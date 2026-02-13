# Configuración de Instagram Graph API (paso a paso)

> Objetivo: publicar Reels desde la app usando **subida directa (resumable upload)**, sin Drive.

## 1) Requisitos previos
- Cuenta de Instagram **Business o Creator**.
- Una **Página de Facebook** vinculada a esa cuenta de Instagram.
- Una **App** en Meta for Developers con Instagram Graph API habilitada.
- Tu usuario con **rol de Administrador** sobre la Página y la App.

## 2) Vincular Instagram con la Página de Facebook
> Esto es obligatorio para que aparezca `instagram_business_account`.

**Opción A (desde Instagram móvil)**
1. Perfil → ☰ → **Configuración y privacidad**.
2. **Cuenta** → **Cambiar a cuenta profesional** (si aún no lo es).
3. **Vincular a Facebook** → selecciona o crea una Página.

**Opción B (desde Facebook / Business Suite)**
1. Business Suite → **Configuración**.
2. **Cuentas → Cuentas de Instagram** → **Agregar**.
3. Selecciona la cuenta IG y confirma.
4. En **Cuentas → Páginas** confirma que la Página tenga la IG vinculada.

## 3) Crear App en Meta for Developers
1. Entra a **Meta for Developers** → **Mis aplicaciones** → **Crear app**.
2. Tipo recomendado: **Business**.
3. En el panel de la app, habilita **Instagram Graph API**.

## 4) Permisos requeridos
Estos permisos son obligatorios para publicar Reels:
- `instagram_basic`
- `instagram_content_publish`
- `pages_show_list`
- `pages_read_engagement`

Si tu app está en **Development**, estos permisos solo funcionan para usuarios **con rol dentro de la app**.

## 5) Obtener el Instagram Account ID
Usa el **Graph API Explorer**:

1. Selecciona tu app.
2. Genera un **User Access Token** con los permisos del paso 4.
3. Ejecuta:

```
GET /me/accounts?fields=name,instagram_business_account
```

Respuesta esperada:
```
{
  "data": [
    {
      "name": "Mi Página",
      "id": "<PAGE_ID>",
      "instagram_business_account": {
        "id": "<IG_ACCOUNT_ID>"
      }
    }
  ]
}
```

> El **Instagram Account ID** es el valor dentro de `instagram_business_account.id`.

Si no aparece `instagram_business_account`, la cuenta IG **no está vinculada** a la Página.

## 6) Generar Access Token válido
En Graph API Explorer:
1. Selecciona la app correcta.
2. Marca permisos del paso 4.
3. Genera **User Access Token**.
4. Copia el token completo sin espacios ni saltos.

## 7) Configurar la app local
En **Transcriptor de Video → Instagram → Configuración**:
- **Instagram Account ID**: pega el `instagram_business_account.id`.
- **Access Token**: pega el token generado.
- Click en **Guardar Credenciales**.

## 8) OAuth con Redirect URI (cuando uses "Conectar con Facebook")
La app levanta un servidor local para capturar el `code`.
- **Redirect URI recomendado**: `http://127.0.0.1:8766/callback`
- **Puerto correcto**: `8766` (es el que escucha la app).

Si usas **ngrok**:
- Inicia ngrok apuntando al puerto correcto: `ngrok http 8766`
- Usa el dominio de ngrok como Redirect URI en Meta.
- Si ngrok apunta a `8000`, verás `ERR_NGROK_8012` / `502` porque no hay servicio en ese puerto.

## 9) Publicar Reel (subida directa)
En **Instagram → Subir Reel**:
1. Selecciona el archivo `.mp4`.
2. Escribe caption.
3. Click en **Publicar en Instagram**.

La app usa **resumable upload** (directo a servidores de Instagram), sin Drive.

## 10) Errores comunes
- **Error 190 (Cannot parse access token)**: token inválido o mal copiado.
- **Error 100 / subcode 33**: estás usando ID de Página en lugar del IG Account ID.
- **No aparece instagram_business_account**: IG no está vinculada a la Página.
- **API access deactivated**: reactivar en App Dashboard.

## 11) Notas importantes
- Los tokens de usuario expiran; renueva cuando deje de funcionar.
- En **modo Development**, solo los usuarios con rol en la app pueden publicar.
