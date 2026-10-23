# Stem Separator para Windows y macOS

Aplicación de escritorio en español para importar una mezcla **WAV, MP3 o FLAC**,
o el audio de un **vídeo MP4**, y
exportar los stems seleccionados como **WAV PCM de 24 bits** o **MP3 de 320 kbps**.
Salida estéreo, 44,1 kHz. Procesamiento local: el audio no se sube a ningún servicio.

- Batería, bajo, voz principal, coros, guitarra, piano y otros.
- Selección independiente de archivos que exportar en cada ejecución.
- Carpetas numeradas para no sobrescribir separaciones anteriores.
- Cancelación entre etapas, registro de errores y manifiesto de cada separación.
- Interfaz nativa Tk; instalador por usuario, sin permisos de administrador.
- Vista oscura con una fila de color por instrumento, formas de onda reales y
  escucha individual de los resultados en Windows y macOS. Inspiración visual en estaciones
  de audio como Logic Pro, sin usar su código, recursos ni modelos propietarios.
- Cursor de reproducción independiente por pista: clic o arrastre sobre la onda
  para escuchar desde ese instante, con indicador de tiempo y avance durante la escucha.

## Instalación en Windows 10/11 x64

Descarga el instalador desde [Releases](https://github.com/jguillenconesa-coder/Stem-separator/releases/latest):
`StemSeparator-Setup-0.3.0-x64.exe`. Instálalo sin permisos de administrador.
No requiere Python instalado. El instalador no tiene firma de editor.

## Instalación en macOS 15 o posterior

En la misma release hay dos imágenes de disco:

- **Apple Silicon (M1 o posterior)**: `StemSeparator-0.3.0-macOS-arm64.dmg`.
- **Intel**: `StemSeparator-0.3.0-macOS-x86_64.dmg`.

Abre el DMG y arrastra **Stem Separator.app** a **Aplicaciones**. Son paquetes
nativos separados, con las mismas funciones, sin necesitar Rosetta, Python o FFmpeg.
Las versiones anteriores de macOS/OS X no están verificadas ni soportadas por estos paquetes.
La app tiene firma ad hoc, sin notarización de Apple: tras intentar abrirla, puede
ser necesario autorizarla en **Ajustes del Sistema → Privacidad y seguridad → Abrir igualmente**.
No es necesario desactivar Gatekeeper. Los checksums SHA256 acompañan las descargas.

La release se publica automáticamente solo si Windows y ambas arquitecturas Mac
pasan las pruebas de código, modelos reales e instalación. Mientras se construye,
los paquetes verificados de cada plataforma también aparecen en los artefactos de
**Actions → Desktop installers**.

Recomendado: 16 GB de RAM, varios GB libres y CPU de 64 bits. La distribución
usa CPU para ser compatible con equipos sin GPU. La primera separación
necesita Internet para descargar pesos y metadatos; puede tardar. Las siguientes
reutilizan la caché. No se garantiza funcionamiento sin red: audio-separator puede
consultar metadatos de sus modelos incluso con los pesos presentes.

1. Elige un WAV, MP3, FLAC o vídeo MP4 y la carpeta de salida. En MP4 se usa la
   primera pista de audio; un vídeo sin audio muestra un error explicativo.
2. Marca los stems deseados y el formato.
3. Mantén «Distinguir voz principal y coros» para separarlos, o desactívalo y
   desmarca Coros para obtener todas las voces juntas en `vocals`.
4. Pulsa **Separar y exportar**. La cancelación espera a que acabe la etapa actual.
5. Escucha una pista con **▶ Escuchar**, detén la reproducción con **■ Detener**,
   o abre los resultados. Cada ejecución incluye `separation.json`.
6. Haz clic o arrastra el cursor sobre la forma de onda para saltar a otro momento.
   Las flechas izquierda/derecha desplazan 5 segundos cuando la onda tiene el foco;
   Espacio reproduce desde el cursor. Detener conserva la posición de cada pista.
   Se escucha una pista a la vez. La primera escucha prepara un WAV temporal;
   los siguientes saltos usan el reproductor nativo de cada sistema (WinMM en Windows y AVFoundation en macOS), sin volver a convertir.

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

En macOS, instala Python 3.11 con Tk y Homebrew, después:

```bash
brew install libsamplerate
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt pytest==8.3.5 pyinstaller==6.12.0
python packaging/prepare_macos.py
python -m pytest -q
python -m stem_separator
# Para generar el DMG nativo:
bash packaging/build_macos.sh
```

Mac Intel usa audio-separator 0.24.1 y PyTorch 2.2.2, la última línea con ruedas
oficiales de PyTorch para Intel; Apple Silicon y Windows usan audio-separator
0.30.2 y PyTorch 2.5.1. Un adaptador de escritura comparte el mismo flujo de stems
y conserva el audio flotante entre etapas. No se omiten las pruebas en Intel.

Tk viene con Python para Windows. En Linux se necesita Tk y un servidor gráfico
para la interfaz. FFmpeg se obtiene de imageio-ffmpeg. Caché y registro en Windows:
`%LOCALAPPDATA%/StemSeparator`; en macOS: `~/Library/Application Support/StemSeparator`;
en Linux: `~/.cache/StemSeparator`. Desinstalar la app no elimina automáticamente
los modelos de esa carpeta.

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
instalado. Genera el instalador Windows, los DMG Intel/Apple Silicon y sus SHA256, y publica
una release con esos archivos cuando todas las plataformas pasan. La firma con
certificado de editor de Windows y la notarización de Apple no están configuradas. Las dependencias directas están fijadas; las transitivas
se resuelven al instalar, por lo que no es un build reproducible bit a bit.

## Créditos

Demucs: Meta Research; audio-separator: Andrew Beveridge / Nomad Karaoke;
modelos Karaoke: comunidad Ultimate Vocal Remover / Anjok07 / TRvlvr.
Consulta [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) y las licencias incluidas.
Código propio: MIT, jguillenconesa-coder.
