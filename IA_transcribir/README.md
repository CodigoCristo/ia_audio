# WhisperX Ultra-Pro

Herramienta de transcripción y generación de subtítulos basada en **WhisperX**, con sincronización milimétrica por palabra, limpieza de texto y exportación a múltiples formatos (SRT, VTT, ASS).

---

## Requisitos del sistema

- **OS:** Arch Linux
- **Python:** 3.12 (ver instrucciones abajo)
- **ffmpeg** instalado en el sistema
- GPU NVIDIA opcional (para aceleración CUDA)

---

## 1. Instalar Python 3.12

Python 3.12 no está en los repositorios oficiales de Arch, se instala desde el **AUR** usando `yay`:

```bash
yay -Syu python312
curl https://bootstrap.pypa.io/get-pip.py | python3.12
```

Verificar que quedó instalado correctamente:

```bash
python3.12 --version
```

---

## 2. Instalar ffmpeg

```bash
sudo pacman -S ffmpeg
```

---

## 3. Instalar dependencias de Python

### 3a. PyTorch (CPU)

Si **no** tienes GPU NVIDIA o no vas a usar CUDA:

```bash
python3.12 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 3b. PyTorch (GPU con CUDA)

Si tienes GPU NVIDIA, primero verifica tu versión de CUDA:

```bash
nvidia-smi
```

Luego instala la versión correspondiente (ejemplo para CUDA 12.1):

```bash
python3.12 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3c. WhisperX y el resto de dependencias

```bash
python3.12 -m pip install whisperx
```

---

## 4. Verificar instalación

```bash
python IA_whisper.py --help
```

Si ves el menú de ayuda, todo está en orden.

---

## Modelos disponibles

Whisper ofrece **7 modelos** con diferente balance entre velocidad y precisión. Se descargan automáticamente la primera vez que se usan y se guardan en caché:

| Modelo | Parámetros | Peso aprox. | Velocidad | Precisión | Recomendado para |
|---|---|---|---|---|---|
| `tiny` | 39 M | ~75 MB | ⚡⚡⚡⚡⚡ | ★☆☆☆☆ | Pruebas rápidas, borradores |
| `base` | 74 M | ~145 MB | ⚡⚡⚡⚡ | ★★☆☆☆ | Uso general básico |
| `small` | 244 M | ~465 MB | ⚡⚡⚡ | ★★★☆☆ | Buena relación calidad/velocidad |
| `medium` | 769 M | ~1.5 GB | ⚡⚡ | ★★★★☆ | Producción estándar *(default)* |
| `large-v1` | 1550 M | ~3.0 GB | ⚡ | ★★★★☆ | Alta precisión (generación antigua) |
| `large-v2` | 1550 M | ~3.0 GB | ⚡ | ★★★★★ | Mejor que v1 en la mayoría de idiomas |
| `large-v3` | 1550 M | ~3.0 GB | ⚡ | ★★★★★ | Máxima precisión, recomendado para producción |

```bash
# Elegir modelo con -m
python3.12 IA_whisper.py audio.mp3 -m tiny       # rápido
python3.12 IA_whisper.py audio.mp3 -m medium     # default
python3.12 IA_whisper.py audio.mp3 -m large-v3   # máxima calidad
```

> Los modelos `large` requieren al menos **8 GB de RAM** (CPU) o **6 GB de VRAM** (GPU).

---

## Idiomas soportados

Whisper soporta más de **90 idiomas**. Se especifican con el código ISO 639-1 usando `-l`. Si no se indica, el idioma se detecta automáticamente en los primeros segundos del audio.

Algunos de los idiomas más usados:

| Código | Idioma | Código | Idioma |
|---|---|---|---|
| `es` | Español | `zh` | Chino (mandarín) |
| `en` | Inglés | `ja` | Japonés |
| `fr` | Francés | `ko` | Coreano |
| `de` | Alemán | `ar` | Árabe |
| `pt` | Portugués | `ru` | Ruso |
| `it` | Italiano | `hi` | Hindi |
| `nl` | Holandés | `tr` | Turco |
| `pl` | Polaco | `vi` | Vietnamita |
| `sv` | Sueco | `id` | Indonesio |
| `uk` | Ucraniano | `th` | Tailandés |

```bash
# Especificar idioma manualmente (más rápido y preciso)
python3.12 IA_whisper.py audio.mp3 -l es   # español
python3.12 IA_whisper.py audio.mp3 -l en   # inglés
python3.12 IA_whisper.py audio.mp3 -l ja   # japonés

# Detección automática (sin -l)
python3.12 IA_whisper.py audio.mp3
```

> Especificar el idioma manualmente siempre es más rápido y reduce errores en audios cortos o con ruido.

---

## Uso básico

```bash
python IA_whisper.py <archivo_de_audio> [opciones]
```

El archivo de entrada puede ser `.mp3`, `.mp4`, `.wav`, `.mkv`, `.ogg`, etc. ffmpeg se encarga de la conversión automáticamente.

---

## Ejemplos de uso

### Transcripción simple (detección automática de idioma)

```bash
python IA_whisper.py video.mp4
```

### Especificar idioma y carpeta de salida

```bash
python IA_whisper.py podcast.mp3 -l es -o ./subtitulos/
```

### Usar el modelo más preciso

```bash
python IA_whisper.py audio.mp3 -m large-v3
```

### Exportar en todos los formatos (SRT + VTT + ASS)

```bash
python IA_whisper.py audio.mp3 -f all
```

### Subtítulos con máximo 4 palabras por línea

```bash
python IA_whisper.py audio.mp3 --max-words 4
```

### Cortar subtítulo si hay más de 0.5s de silencio

```bash
python IA_whisper.py audio.mp3 --max-silence 0.5
```

---

## Transformación de texto (`--case`)

Controla las mayúsculas/minúsculas del texto final:

| Opción | Resultado | Ejemplo |
|---|---|---|
| `--case upper` | Todo en mayúsculas | `hola mundo` → `HOLA MUNDO` |
| `--case lower` | Todo en minúsculas | `HOLA MUNDO` → `hola mundo` |
| `--case title` | Cada palabra capitalizada | `hola mundo` → `Hola Mundo` |
| `--case capitalize` | Solo la primera letra | `hola mundo` → `Hola mundo` |

```bash
# Subtítulos estilo cine (todo en caps)
python IA_whisper.py film.mp4 --case upper

# Estilo más natural
python IA_whisper.py video.mp4 --case capitalize
```

---

## Limpieza de puntuación (`--no-punctuation`)

```bash
# Eliminar puntos, comas, exclamación e interrogación
python IA_whisper.py audio.mp3 --no-punctuation ".,!?"

# Eliminar toda la puntuación común
python IA_whisper.py audio.mp3 --no-punctuation all

# Combinar con mayúsculas
python IA_whisper.py audio.mp3 --no-punctuation all --case upper
```

---

## Usar GPU (CUDA)

```bash
# GPU con float16 (más rápido, menos VRAM)
python IA_whisper.py audio.mp3 --device cuda --compute-type float16

# GPU con int8 (mínimo uso de VRAM)
python IA_whisper.py audio.mp3 --device cuda --compute-type int8
```

---

## Precisión de transcripción

```bash
# Máxima precisión (más lento)
python IA_whisper.py audio.mp3 --beam-size 10 --patience 2.0

# Más rápido / ligero
python IA_whisper.py audio.mp3 --beam-size 2 --patience 0.5

# Temperatura para audios difíciles o ruidosos
python IA_whisper.py audio.mp3 --temperature 0.4
```

---

## Combinaciones recomendadas para producción

### YouTube en español — limpio y bien segmentado

```bash
python IA_whisper.py video.mp4 \
  -l es -m large-v3 \
  --max-words 3 \
  --no-punctuation ".,!?¡¿" \
  --case capitalize \
  -o ./subs/
```

### Subtítulos estilo cine (inglés, mayúsculas, formato ASS)

```bash
python IA_whisper.py film.mp4 \
  -l en -m large-v3 \
  --case upper \
  --no-punctuation all \
  -f ass \
  -o ./subs/
```

### Borrador rápido para revisión

```bash
python IA_whisper.py borrador.mp3 -m tiny -f vtt -o ./draft/
```

### Máxima calidad con GPU — todos los formatos

```bash
python IA_whisper.py master.wav \
  -l es -m large-v3 \
  --device cuda --compute-type float16 \
  --beam-size 10 --patience 2.0 \
  --max-words 3 --case capitalize \
  -f all -o ./final/
```

---

## Referencia de parámetros

| Parámetro | Default | Descripción |
|---|---|---|
| `input` | — | Archivo de audio/video de entrada |
| `-l`, `--language` | auto | Código ISO del idioma (`es`, `en`, `fr`…) |
| `-m`, `--model` | `medium` | Modelo Whisper: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `-f`, `--format` | `srt` | Formato de salida: `srt`, `vtt`, `ass`, `all` |
| `-o`, `--output-dir` | `./subs/` | Carpeta de destino |
| `--max-words` | `2` | Palabras máximas por línea |
| `--max-silence` | `0.1` | Segundos de silencio para forzar corte |
| `--case` | sin cambios | `upper` / `lower` / `title` / `capitalize` |
| `--no-punctuation` | ninguno | Chars a eliminar o `all` |
| `--beam-size` | `5` | Tamaño del beam search (1–10) |
| `--patience` | `1.0` | Factor de paciencia del beam search |
| `--temperature` | `0.0` | Temperatura de muestreo |
| `--no-speech-threshold` | `0.6` | Umbral para descartar segmentos sin voz |
| `--compression-ratio-threshold` | `2.4` | Umbral anti-alucinaciones |
| `--vad-onset` | `0.500` | Umbral de inicio de voz (VAD) |
| `--vad-offset` | `0.363` | Umbral de fin de voz (VAD) |
| `--device` | `cpu` | `cpu` o `cuda` |
| `--compute-type` | `float32` | `float32`, `float16` o `int8` |

---

## Salida generada

Cada ejecución genera los archivos en la carpeta de salida con el mismo nombre del archivo de entrada:

```
subs/
├── mi_video.srt
├── mi_video.vtt          # solo con -f vtt o -f all
├── mi_video.ass          # solo con -f ass o -f all
└── mi_video_confidence.txt   # reporte de segmentos dudosos
```

El archivo `_confidence.txt` lista automáticamente los segmentos con baja confianza (< 0.70) y los que tuvieron timestamps interpolados, útil para revisión manual.
