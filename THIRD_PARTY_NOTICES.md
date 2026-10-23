# Créditos y componentes de terceros

La aplicación integra trabajos de terceros; no presenta sus modelos como propios.
La licencia MIT del código de esta aplicación no sustituye sus licencias.

| Componente | Autores / fuente | Licencia del código |
| --- | --- | --- |
| Demucs y arquitectura htdemucs_6s | Meta / Facebook Research y colaboradores, https://github.com/facebookresearch/demucs | MIT |
| audio-separator | Andrew Beveridge / Nomad Karaoke y colaboradores, https://github.com/nomadkaraoke/python-audio-separator | MIT |
| Ultimate Vocal Remover, modelos Karaoke | Anjok07, TRvlvr y colaboradores, https://github.com/Anjok07/ultimatevocalremovergui y https://github.com/TRvlvr/model_repo | Código UVR: MIT; pesos: consultar distribución original |
| PyTorch / torchaudio / torchvision | PyTorch Foundation, Meta y colaboradores, https://pytorch.org | BSD y avisos incluidos |
| ONNX / ONNX Runtime | ONNX y Microsoft y colaboradores | Apache-2.0 / MIT |
| NumPy / SciPy / SoundFile / librosa | Sus respectivos colaboradores | BSD / BSD / BSD y libsndfile LGPL / ISC |
| FFmpeg | Proyecto FFmpeg, https://ffmpeg.org | LGPL/GPL según compilación |
| imageio-ffmpeg | Proyecto imageio, https://github.com/imageio/imageio-ffmpeg | BSD-2-Clause; FFmpeg tiene licencia independiente |
| Python / Tcl / Tk | Python Software Foundation y colaboradores Tcl/Tk | PSF / Tcl-Tk |
| Inno Setup | Jordan Russell, Martijn Laan y colaboradores, https://jrsoftware.org | Licencia Inno Setup |

## Pesos de modelos

Los pesos no se incluyen en el instalador. Se descargan desde los distribuidores
originales en el primer uso y quedan en `%LOCALAPPDATA%/StemSeparator/models`.
Demucs utiliza `htdemucs_6s.yaml` y `5c90dfd2-34c22ccb.th`; la segunda etapa usa
`UVR_MDXNET_KARA_2.onnx`. Los créditos públicos del repositorio UVR no permiten
atribuir inequívocamente este peso a una persona concreta: se acredita al proyecto
sin inventar autoría ni afirmar que todos los pesos sean MIT. Consulta sus términos
originales antes de redistribuir pesos o hacer una distribución comercial.

## Distribución binaria

El proceso de compilación copia los archivos LICENSE/NOTICE/COPYING de las
dependencias instaladas a `licenses/`. FFmpeg se distribuye mediante la rueda de
imageio-ffmpeg: sus builds pueden incluir GPL y libmp3lame. Para un binario
redistribuido deben conservarse los avisos y cumplirse las obligaciones de fuente
del build concreto. Fuentes e instrucciones del proveedor:
https://github.com/imageio/imageio-ffmpeg y https://github.com/BtbN/FFmpeg-Builds.
No se declara que el instalador completo tenga únicamente licencia MIT.


## Integración macOS

La reproducción utiliza AVFoundation y Foundation de Apple, mediante PyObjC
(Ronald Oussoren y colaboradores, MIT; https://github.com/ronaldoussoren/pyobjc).
Los frameworks del sistema no se redistribuyen. libsamplerate (Erik de Castro Lopo
y colaboradores, BSD-2-Clause; https://github.com/libsndfile/libsamplerate) se
obtiene de Homebrew para la arquitectura nativa. Sus avisos se conservan junto a
los de las dependencias. Intel utiliza audio-separator 0.24.1 y PyTorch 2.2.2;
Apple Silicon utiliza audio-separator 0.30.2 y PyTorch 2.5.1.
