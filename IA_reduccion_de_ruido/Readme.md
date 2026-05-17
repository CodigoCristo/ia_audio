# IA_noise_audio — Reducción de ruido y Super Resolution de audio

Script para procesar audio con IA en CPU. Dos modos:

- **Denoise** (default) — elimina ruido con DeepFilterNet3
- **Super Resolution** (`--superres`) — mejora calidad y frecuencia de muestreo con Vocos
- **Pipeline automático** — usando `--superres` y `--atten-lim` juntos ejecuta denoise → superres en un solo comando

---

## Requisitos del sistema

- **OS:** Arch Linux
- **Python 3.12** — no usar 3.13 ni 3.14, tienen incompatibilidades con torchaudio
- **Rust** — requerido para compilar dependencias de DeepFilterNet durante la instalación
- **ffmpeg** — para convertir formatos de audio (mp3, m4a, opus, mp4, mkv, etc.)

---

## 1. Instalar Python 3.12

Python 3.12 no está en los repositorios oficiales de Arch, se instala desde el AUR:

```bash
yay -S python312
curl https://bootstrap.pypa.io/get-pip.py | python3.12
```

---

## 2. Instalar Rust

DeepFilterNet requiere Rust para compilar extensiones nativas durante `pip install`. Sin Rust la instalación falla con errores de compilación.

```bash
sudo pacman -S rust
```

Verificar que quedó instalado:

```bash
rustc --version
cargo --version
```

---

## 3. Instalar ffmpeg

```bash
sudo pacman -S ffmpeg
```

---

## 4. Instalar dependencias de Python

### Dependencias base (requeridas para ambos modos)

```bash
python3.12 -m pip install soundfile scipy
python3.12 -m pip install torch==2.2.0 torchaudio==2.2.0 \
    --index-url https://download.pytorch.org/whl/cpu
```

> **Importante:** usar exactamente `torch==2.2.0` y `torchaudio==2.2.0`. Las versiones 2.3+ son incompatibles con deepfilternet.

### Para reducción de ruido (`--denoise`, modo default)

```bash
python3.12 -m pip install deepfilternet
```

### Para super resolution (`--superres`)

```bash
python3.12 -m pip install vocos
```

### Instalar todo de una vez

```bash
python3.12 -m pip install soundfile scipy deepfilternet vocos
python3.12 -m pip install torch==2.2.0 torchaudio==2.2.0 \
    --index-url https://download.pytorch.org/whl/cpu
```

---

## Uso básico

```bash
python3.12 IA_noise_audio.py <archivo_de_audio> [opciones]
```

**Formatos de entrada soportados:** wav, flac, ogg, aiff, aif (carga directa) y mp3, m4a, opus, mp4, mkv y cualquier otro formato que ffmpeg soporte (conversión automática interna con ffmpeg, el temporal se borra al terminar).

Si no se especifica `-o`, el archivo de salida se genera automáticamente en la misma carpeta con el sufijo:
- Modo denoise → `nombre_limpio.wav`
- Modo superres → `nombre_superres.wav`

---

## Argumentos

### Generales

| Argumento | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `input` | str | requerido | Archivo de audio de entrada |
| `-o`, `--output` | str | auto | Archivo de salida (ver sufijos automáticos arriba) |
| `--superres` | flag | False | Activar modo super resolution |
| `--mono` | flag | False | Forzar conversión a mono antes de procesar |
| `--log-level` | str | INFO | Nivel de log: DEBUG, INFO, WARNING, ERROR |

### Reducción de ruido (modo default)

| Argumento | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `--atten-lim` | float | None | Límite de atenuación en dB (ver guía abajo) |
| `--no-pad` | flag | False | No compensar el delay del STFT |
| `--df-model` | str | None | Ruta a modelo DeepFilterNet alternativo en disco |

### Super resolution (`--superres`)

| Argumento | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `--sr-model` | str | general | Modelo Vocos: `general` o `voice` |
| `--target-sr` | int | 24000 | Frecuencia de salida en Hz: `24000` o `48000` |

---

## Guía de `--atten-lim`

Controla qué tan agresivo es el filtro de ruido. Se mide en dB:

```
Sin --atten-lim    → atenuación máxima, elimina todo el ruido posible (puede sonar artificial)
--atten-lim 100    → muy agresivo, puede afectar levemente la voz
--atten-lim 55     → equilibrado, recomendado para voz con ruido moderado
--atten-lim 30     → suave, conserva algo de ambiente natural
--atten-lim 10     → mínimo, casi sin cambios perceptibles
```

Si el resultado suena distorsionado o metálico, bajar el valor a 30 o 20.

---

## Pipeline automático: denoise → superres

Si se pasan `--superres` y `--atten-lim` **juntos en el mismo comando**, el script ejecuta automáticamente las dos etapas en memoria sin escribir archivos intermedios:

1. Primero aplica DeepFilterNet3 (reducción de ruido)
2. Luego pasa el resultado directo a Vocos (super resolution)
3. Guarda solo el archivo final

```bash
# Un solo comando que hace denoise + superres
python3.12 IA_noise_audio.py grabacion.mp3 \
    --atten-lim 55 --superres --target-sr 48000 -o final.wav
```

Esto es equivalente a los dos pasos manuales de abajo, pero más rápido porque el audio no se escribe ni se vuelve a leer del disco entre etapas.

---

## Comportamiento con audio estéreo

**Modo denoise:** procesa cada canal (L y R) de forma independiente con DeepFilterNet3 y reconstruye el estéreo al final. La reducción de ruido se aplica correctamente a ambos canales.

**Modo superres:** procesa L y R por separado con Vocos y aplica normalización RMS automática al canal derecho para evitar desbalance de volumen entre canales. El estéreo se preserva en la salida.

Para forzar que todo se procese en mono (más rápido, menos memoria):

```bash
python3.12 IA_noise_audio.py audio_stereo.wav --mono
python3.12 IA_noise_audio.py audio_stereo.wav --superres --mono
```

---

## Ejemplos

### Reducción de ruido

```bash
# Reducción máxima (default, sin límite)
python3.12 IA_noise_audio.py grabacion.wav
# → genera grabacion_limpio.wav

# Reducción equilibrada (recomendada para voz)
python3.12 IA_noise_audio.py grabacion.wav --atten-lim 55

# Con nombre de salida personalizado
python3.12 IA_noise_audio.py grabacion.wav -o resultado.wav --atten-lim 55

# Desde mp3 directamente (ffmpeg convierte internamente)
python3.12 IA_noise_audio.py cancion.mp3 -o limpia.wav --atten-lim 55

# Forzar mono (más rápido)
python3.12 IA_noise_audio.py grabacion.wav -o voz_limpia.wav --mono

# Reducción suave, conservar ambiente
python3.12 IA_noise_audio.py ambiente.wav --atten-lim 20
```

### Super resolution

```bash
# Super resolution a 24kHz (nativo de Vocos)
python3.12 IA_noise_audio.py audio_bajo.wav --superres
# → genera audio_bajo_superres.wav

# Super resolution a 48kHz
python3.12 IA_noise_audio.py audio_bajo.wav --superres --target-sr 48000 -o audio_hd.wav

# Modelo optimizado para voz
python3.12 IA_noise_audio.py voz.wav --superres --sr-model voice

# Desde mp3 a 48kHz
python3.12 IA_noise_audio.py podcast.mp3 --superres --target-sr 48000 -o podcast_hd.wav
```

### Pipeline automático (denoise + superres en un solo comando)

```bash
# Denoise equilibrado + superres a 24kHz
python3.12 IA_noise_audio.py grabacion.mp3 --atten-lim 55 --superres

# Denoise + superres a 48kHz con salida personalizada
python3.12 IA_noise_audio.py grabacion.mp3 \
    --atten-lim 55 --superres --target-sr 48000 -o final.wav

# Máxima limpieza + superres para voz grabada con mal micrófono
python3.12 IA_noise_audio.py entrevista.mp3 \
    --atten-lim 55 --superres --sr-model voice --target-sr 48000 -o entrevista_hd.wav
```

### Pipeline manual (dos pasos separados)

```bash
# Paso 1: limpiar ruido
python3.12 IA_noise_audio.py grabacion.mp3 -o limpio.wav --atten-lim 55

# Paso 2: mejorar calidad
python3.12 IA_noise_audio.py limpio.wav --superres --target-sr 48000 -o final.wav
```

### Diagnóstico y depuración

```bash
# Ver información detallada del procesamiento
python3.12 IA_noise_audio.py audio.wav --log-level DEBUG
```

Con `DEBUG` se muestran: sample rate detectado, dimensiones del array de audio, operaciones de resampleo, tiempos de carga del modelo y pasos internos de conversión.

---

## Cómo funciona cada modo

### DeepFilterNet3 (denoise)

Red neuronal de dos etapas para eliminación de ruido:

1. **Etapa ERB** — filtra en bandas de frecuencia tipo Equivalent Rectangular Bandwidth, similar a como percibe el oído humano.
2. **Etapa DF (Deep Filtering)** — aplica filtros complejos en frecuencia para recuperar detalles finos de la voz.

Trabaja internamente a **48kHz**. El audio se resamplea automáticamente si tiene otra frecuencia.

### Vocos (superres)

Vocoder neuronal basado en ConvNeXt que reconstruye audio de alta calidad a partir de mel spectrograms. Mejora la calidad perceptual subiendo frecuencias perdidas o degradadas. Trabaja a **24kHz** de forma nativa; con `--target-sr 48000` resamplea la salida.

Especialmente útil para audio grabado con micrófonos de baja calidad, audio comprimido (mp3 de baja tasa), o grabaciones de voz por teléfono.

---

## Problemas conocidos

**Error de compilación al instalar deepfilternet** — falta Rust. Instalar con `sudo pacman -S rust` y volver a ejecutar pip install.

**`torchaudio.backend` not found** — instalar exactamente `torchaudio==2.2.0`.

**Segfault con torchaudio.load** — el script usa `soundfile` para cargar audio, evitando completamente este problema.

**Segfault con torchvision** — `torchvision` actualiza torch a versiones 2.3+ rompiendo torchaudio. No instalar torchvision en el mismo entorno.

**Audio muy distorsionado o metálico con denoise** — bajar `--atten-lim` a 30 o 20.
