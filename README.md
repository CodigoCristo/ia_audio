<div align="center">

```
██╗ █████╗     █████╗ ██╗   ██╗██████╗ ██╗ ██████╗
██║██╔══██╗   ██╔══██╗██║   ██║██╔══██╗██║██╔═══██╗
██║███████║   ███████║██║   ██║██║  ██║██║██║   ██║
██║██╔══██║   ██╔══██║██║   ██║██║  ██║██║██║   ██║
██║██║  ██║   ██║  ██║╚██████╔╝██████╔╝██║╚██████╔╝
╚═╝╚═╝  ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝
```

**Herramientas de procesamiento de audio con Inteligencia Artificial**  
*Separación de stems · Reducción de ruido · Super resolución · Transcripción*

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Arch_Linux-1793D1?style=flat-square&logo=arch-linux&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)
![CPU](https://img.shields.io/badge/CPU-Compatible-orange?style=flat-square)
![CUDA](https://img.shields.io/badge/CUDA-Opcional-76b900?style=flat-square&logo=nvidia&logoColor=white)

</div>

---

## ¿Qué es esto?

Colección de scripts Python para procesar audio y video con modelos de IA de última generación, pensados para correr **localmente en CPU** (con soporte opcional de GPU NVIDIA). Sin APIs externas, sin límites de uso, sin costos por minuto.

Cada herramienta es independiente: úsalas por separado o encadénalas para crear flujos de trabajo de producción completos.

---

## Módulos

### 🎛️ [IA_audio_separator](./IA_audio_separator/)
**Separación de fuentes de audio — Demucs `htdemucs_6s`**

Separa cualquier canción o video en sus 6 componentes individuales usando el modelo de Meta AI. Extrae, mezcla o exporta en cualquier combinación.

| Stem | Contenido |
|------|-----------|
| `vocals` | Voz principal y coros |
| `drums` | Batería y percusión |
| `bass` | Bajo eléctrico o acústico |
| `guitar` | Guitarra eléctrica o acústica |
| `piano` | Piano, teclados y sintetizadores |
| `other` | Todo lo demás |

```bash
# Pista karaoke (todo sin voz)
python3.12 IA_audio_separator.py cancion.mp3 --preset karaoke

# Los 6 stems por separado
python3.12 IA_audio_separator.py cancion.mp3 --preset all

# Combinación libre
python3.12 IA_audio_separator.py cancion.mp3 --preset vocals+guitar+piano
```

---

### 🔇 [IA_reduccion_de_ruido](./IA_reduccion_de_ruido/)
**Limpieza de audio e interpolación — DeepFilterNet3 + Vocos**

Dos modos que pueden ejecutarse solos o en pipeline automático:

- **Denoise** — elimina ruido de fondo con DeepFilterNet3 (red neuronal de dos etapas, trabaja a 48kHz internamente)
- **Super Resolution** — reconstruye frecuencias perdidas y mejora calidad perceptual con Vocos hasta 48kHz

```bash
# Limpieza equilibrada para voz
python3.12 IA_noise_audio.py grabacion.mp3 --atten-lim 55

# Pipeline completo: denoise → superres en un solo comando
python3.12 IA_noise_audio.py grabacion.mp3 \
    --atten-lim 55 --superres --target-sr 48000 -o final.wav
```

---

### 🗣️ [IA_transcribir](./IA_transcribir/)
**Transcripción y subtítulos — WhisperX Ultra-Pro**

Genera subtítulos con sincronización milimétrica por palabra a partir de cualquier audio o video. Exporta a SRT, VTT y ASS con control total sobre el formato del texto.

```bash
# YouTube en español, estilo limpio
python3.12 IA_whisper.py video.mp4 \
  -l es -m large-v3 \
  --max-words 3 \
  --no-punctuation ".,!?¡¿" \
  --case capitalize \
  -o ./subs/

# Subtítulos estilo cine (mayúsculas, ASS)
python3.12 IA_whisper.py film.mp4 \
  -l en -m large-v3 --case upper -f ass
```

Soporta más de 90 idiomas. Genera automáticamente un reporte de segmentos con baja confianza para revisión manual.

---

### 📝 [IA_texto_a_audio](./IA_texto_a_audio/)
**Text-to-Speech — Edge TTS sincronizado con SRT**

Convierte texto, archivos `.txt` o subtítulos `.srt` en audio usando voces neuronales de Microsoft Edge TTS. Soporta sincronización exacta con video, traducción offline y más de 400 voces en múltiples idiomas.

- Generación de voz desde texto o `.txt`
- Sincronización exacta usando archivos `.srt`
- Traducción offline con `argostranslate`
- Compatible con doblaje automático y narración
- Ajuste automático de velocidad para encajar cada segmento

```bash
# Texto simple
python3.12 IA_edge_tts.py \
    --text "Hola, esto es una prueba de voz." \
    --voice es-MX-DaliaNeural -o prueba.wav

# Desde un archivo TXT
python3.12 IA_edge_tts.py \
    --txt-file narracion.txt \
    --voice es-MX-JorgeNeural -o narracion.wav

# Generar TTS sincronizado desde un SRT
python3.12 IA_edge_tts.py \
    --sub ./subs/video.srt --audio video.wav \
    -o video_tts.wav

# Traducir subtítulos y generar doblaje
python3.12 IA_edge_tts.py \
    --translate es en \
    --sub ./subs/video.srt --audio video.wav \
    -o video_en.wav
```

Soporta más de 400 voces neuronales en más de 100 idiomas mediante Microsoft Edge TTS.

---

## Requisitos comunes

Todos los módulos comparten la misma base:

```bash
# Python 3.12 desde AUR
yay -S python312
curl https://bootstrap.pypa.io/get-pip.py | python3.12

# ffmpeg (requerido por todos los módulos)
sudo pacman -S ffmpeg
```

Cada módulo tiene sus propias dependencias de Python documentadas en su carpeta.

---

## Compatibilidad de hardware

| Hardware | Soporte | Notas |
|----------|---------|-------|
| CPU (cualquier x86-64) | ✅ Completo | 5–10 min por canción en separación |
| GPU NVIDIA (CUDA) | ✅ Recomendado | 5–10× más rápido |
| Apple Silicon (MPS) | ✅ Parcial | Solo `IA_audio_separator` |
| GPU AMD (ROCm) | ⚠️ No probado | — |

---

<div align="center">

Hecho con Python · Arch Linux · Meta Demucs · DeepFilterNet · Vocos · WhisperX

</div>
