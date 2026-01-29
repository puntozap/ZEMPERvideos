# Crear instalador (Windows)

Este documento describe el flujo para generar un instalador tipo “Next, Next, Finish”.

## Requisitos
- Python instalado
- FFmpeg en PATH
- Inno Setup instalado

## 1) Empaquetar con PyInstaller
```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile --name TranscriptorVideo app.py
```

El ejecutable queda en:
```
dist\TranscriptorVideo.exe
```

## 2) Crear instalador con Inno Setup
1. Abrir Inno Setup.
2. Crear un nuevo script (o usar el de abajo).
3. Compilar y generar el instalador.

### Script base (.iss)
```ini
[Setup]
AppName=TranscriptorVideo
AppVersion=1.0.0
DefaultDirName={pf}\TranscriptorVideo
DefaultGroupName=TranscriptorVideo
OutputDir=installer
OutputBaseFilename=TranscriptorVideo_Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\TranscriptorVideo.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\TranscriptorVideo"; Filename: "{app}\TranscriptorVideo.exe"
Name: "{commondesktop}\TranscriptorVideo"; Filename: "{app}\TranscriptorVideo.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos"

[Run]
Filename: "{app}\TranscriptorVideo.exe"; Description: "Abrir TranscriptorVideo"; Flags: nowait postinstall skipifsilent
```

## 3) Distribución
El instalador generado queda en la carpeta `installer/`.

## Notas
- Si necesitas incluir ffmpeg embebido, se debe agregar a [Files] y ajustar PATH en instalación.
- Para firmar el instalador, usar un certificado de firma de código.
