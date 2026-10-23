# Stem Separator para Windows

Aplicación de escritorio en español para importar una mezcla **WAV o MP3** y
exportar los stems seleccionados como **WAV PCM de 24 bits** o **MP3 de 320 kbps**.
Salida estéreo, 44,1 kHz. Procesamiento local: el audio no se sube a ningún servicio.

- Batería, bajo, voz principal, coros, guitarra, piano y otros.
- Selección independiente de archivos que exportar en cada ejecución.
- Carpetas numeradas para no sobrescribir separaciones anteriores.
- Cancelación entre etapas, registro de errores y manifiesto de cada separación.
- Interfaz nativa Tk; instalador por usuario, sin permisos de administrador.
- Vista oscura con una fila de color por instrumento, formas de onda reales y
  escucha individual de los resultados en Windows. Inspiración visual en estaciones
  de audio como Logic Pro, sin usar su código, recursos ni modelos propietarios.

## Instalación en Windows 10/11 x64

En GitHub, abre **Actions → Windows installer → ejecución correcta → Artifacts**.
Descarga `StemSeparator-Windows-x64`, descomprime el ZIP y ejecuta
`StemSeparator-Setup-0.1.0-x64.exe`. El archivo SHA256 permite comprobar la descarga.
El instalador no está firmado digitalmente. No requiere Python instalado.
El artefacto solo existe después de una compilación correcta; el código fuente no
constituye un instalador generado.

Recomendado: 16 GB de RAM, varios GB libres y CPU de 64 bits. La distribución
inicial usa CPU para ser compatible con equipos sin GPU. La primera separación
necesita Internet para descargar pesos y metadatos; puede tardar. Las siguientes
reutilizan la caché. No se garantiza funcionamiento sin red: audio-separator puede
consultar metadatos de sus modelos incluso con los pesos presentes.

1. Elige un WAV o MP3 y la carpeta de salida.
2. Marca los stems deseados y el formato.
3. Mantén «Distinguir voz principal y coros» para separarlos, o desactívalo y
   desmarca Coros para obtener todas las voces juntas en `vocals`.
4. Pulsa **Separar y exportar**. La cancelación espera a que acabe la etapa actual.
5. Escucha una pista con **▶ Escuchar**, detén la reproducción con **■ Detener**,
   o abre los resultados. Cada ejecución incluye `separation.json`.

## Modelos y límites

`htdemucs_6s` estima seis instrumentos. Los coros se obtienen pasando su stem de
voces por `UVR_MDXNET_KARA_2`, que estima voz principal y el residual de coros.
Es una separación **experimental**, no una clasificación perfecta de cantantes:
puede contener voz principal, reverberación o perder armonías. Guitarra y piano
también pueden presentar filtraciones. No se promete recuperación de las pistas
originales. No hay aún una evaluación auditiva con música real de referencia.

Elegir menos stems reduce las exportaciones, pero el modelo sigue calculando
los seis instrumentos. Solo se ejecuta la segunda etapa si se solicitan voces o
coros y está activada. MP3 es un formato con pérdidas. Audio mono se convierte a
estéreo duplicando el canal; multicanal se mezcla a estéreo con FFmpeg.

## Desarrollo

Python 3.11 recomendado (3.12 también se prueba en Linux):

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install torch==2.5.1 torchaudio==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt pytest==8.3.5
python -m pip check
python -m pytest -q
python -m stem_separator
```

Tk viene con Python para Windows. En Linux se necesita Tk y un servidor gráfico
para la interfaz. FFmpeg se obtiene de imageio-ffmpeg. Caché y registro en Windows:
`%LOCALAPPDATA%/StemSeparator`; en Linux: `~/.cache/StemSeparator`.

Prueba de inferencia real (descarga modelos, no evalúa calidad musical):

```powershell
python tests/smoke_models.py
```

Para compilar en Windows, instala **Inno Setup 6**, después:

```powershell
python -m pip install pyinstaller==6.12.0
./packaging/build.ps1
```

GitHub Actions ejecuta pruebas y la inferencia real antes de empaquetar. Después
instala el ejecutable y comprueba la interfaz y la inferencia desde el paquete
instalado. Genera un instalador x64 y su SHA256. La publicación de una release y la firma digital
no están automatizadas. Las dependencias directas están fijadas; las transitivas
se resuelven al instalar, por lo que no es un build reproducible bit a bit.

## Créditos

Demucs: Meta Research; audio-separator: Andrew Beveridge / Nomad Karaoke;
modelos Karaoke: comunidad Ultimate Vocal Remover / Anjok07 / TRvlvr.
Consulta [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) y las licencias incluidas.
Código propio: MIT, jguillenconesa-coder.
