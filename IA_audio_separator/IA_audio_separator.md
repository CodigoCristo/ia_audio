# IA_audio_separator — Separador de audio con IA

Script para separar los instrumentos y voces de cualquier canción o video usando **Demucs** (Meta AI), modelo `htdemucs_6s`. Extrae hasta 6 stems de forma independiente: vocals, drums, bass, guitar, piano y other.

---

## Requisitos del sistema

- **OS:** Arch Linux
- **Python 3.12**
- **ffmpeg** — para convertir formatos de audio no nativos y video, y para mezclar stems
- GPU NVIDIA opcional (para aceleración CUDA, si no se usa CPU)

---

## 1. Instalar Python 3.12

Python 3.12 no está en los repositorios oficiales de Arch, se instala desde el AUR:

```bash
yay -S python312
curl https://bootstrap.pypa.io/get-pip.py | python3.12
```

Verificar:

```bash
python3.12 --version
```

---

## 2. Instalar ffmpeg

Requerido para convertir mp3, m4a, ogg, opus, video (mp4, mkv...) a WAV internamente, y para exportar en MP3 y mezclar stems en un solo archivo:

```bash
sudo pacman -S ffmpeg
```

---

## 3. Instalar dependencias de Python

```bash
python3.12 -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
python3.12 -m pip install demucs
```

> La primera vez que se ejecute el script, Demucs descarga automáticamente el modelo `htdemucs_6s` (~1 GB). Solo ocurre una vez; queda en caché para usos posteriores.

---

## 4. Verificar instalación

```bash
python3.12 IA_audio_separator.py --list-presets
```

Si ves la lista de presets en color, todo está en orden.

---

## Formatos soportados

**Audio nativo** (carga directa sin conversión): `.wav`, `.flac`

**Audio con conversión automática** (ffmpeg convierte a WAV temporal internamente): `.mp3`, `.m4a`, `.aac`, `.ogg`, `.opus`, `.wma`, `.aiff`

**Video** (ffmpeg extrae el audio automáticamente): `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.m4v`, `.ts`, `.mts`, `.mpeg`, `.mpg`, `.wmv`

En todos los casos el archivo temporal se borra automáticamente al terminar.

---

## Stems disponibles

El modelo `htdemucs_6s` separa 6 elementos independientes:

| Stem | Descripción |
|------|-------------|
| `vocals` | Voz principal y coros |
| `drums` | Batería y percusión |
| `bass` | Bajo eléctrico o acústico |
| `guitar` | Guitarra eléctrica o acústica |
| `piano` | Piano, teclados y sintetizadores |
| `other` | Todo lo que no entra en las categorías anteriores |

---

## Modos de uso

Hay tres formas de indicar qué quieres extraer, son mutuamente excluyentes:

| Modo | Argumento | Cuándo usarlo |
|------|-----------|---------------|
| Preset | `--preset` / `-p` | Combinaciones predefinidas con nombre |
| Stems manuales | `--stems` / `-s` | Elegir stems individualmente |
| Múltiples combos | `--combos` / `-c` | Generar varias combinaciones en un solo comando |

Si no se pasa ninguno de los tres, el script usa `vocals` por defecto.

---

## Presets disponibles

Ver todos en detalle con `--list-presets`. Resumen:

### Voz
| Preset | Stems incluidos | Salida |
|--------|----------------|--------|
| `vocals` | vocals | 1 archivo |
| `vocals+guitar` | vocals, guitar | 1 archivo mezclado |
| `vocals+piano` | vocals, piano | 1 archivo mezclado |
| `vocals+bass` | vocals, bass | 1 archivo mezclado |

### Ritmo
| Preset | Stems incluidos | Salida |
|--------|----------------|--------|
| `drums` | drums | 1 archivo |
| `bass` | bass | 1 archivo |
| `drums+bass` | drums, bass | 1 archivo mezclado |

### Melodía
| Preset | Stems incluidos | Salida |
|--------|----------------|--------|
| `guitar` | guitar | 1 archivo |
| `piano` | piano | 1 archivo |
| `guitar+piano` | guitar, piano | 1 archivo mezclado |

### Mezclas
| Preset | Stems incluidos | Salida |
|--------|----------------|--------|
| `band` | drums, bass, guitar | 1 archivo mezclado |
| `instrumental` | drums, bass, guitar, piano, other | 5 archivos individuales |
| `karaoke` | drums, bass, guitar, piano, other | 1 archivo mezclado (pista sin voz) |
| `other` | other | 1 archivo |

### Completo
| Preset | Stems incluidos | Salida |
|--------|----------------|--------|
| `all` | vocals, drums, bass, guitar, piano, other | 6 archivos individuales |

---

## Argumentos

| Argumento | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `input` | str | requerido | Archivo de audio o video de entrada |
| `--preset`, `-p` | str | — | Nombre de preset o combinación libre con `+` |
| `--stems`, `-s` | list | — | Stems a extraer: `vocals drums bass guitar piano other` |
| `--combos`, `-c` | list | — | Varias combinaciones en un solo comando |
| `--output`, `-o` | str | `audioseparate_<nombre>` | Carpeta de salida |
| `--device`, `-d` | str | `auto` | Dispositivo: `auto`, `cpu`, `cuda`, `mps` |
| `--mp3` | flag | False | Exportar como MP3 320k en vez de WAV (requiere ffmpeg) |
| `--list-presets`, `-l` | flag | — | Mostrar todos los presets y salir |

### Detalle de `--device`

| Valor | Descripción |
|-------|-------------|
| `auto` | Detecta automáticamente: CUDA → MPS → CPU |
| `cpu` | Forzar CPU (compatible con cualquier máquina) |
| `cuda` | GPU NVIDIA con CUDA (mucho más rápido) |
| `mps` | Apple Silicon (M1/M2/M3) |

Sin GPU, el procesamiento en CPU tarda aproximadamente **5-10 minutos por canción** dependiendo de la duración y el hardware.

---

## Archivos de salida

La carpeta de salida se crea automáticamente. Si no se especifica `--output`, se genera con el nombre `audioseparate_<nombre_del_archivo>` en el directorio actual.

El nombre de los archivos generados sigue el patrón:

```
<nombre_base>__<stem_o_preset>.<ext>
```

Ejemplos con `cancion.mp3`:

```
audioseparate_cancion/
├── cancion__vocals.wav          # --preset vocals
├── cancion__drums.wav           # --preset drums
├── cancion__karaoke.wav         # --preset karaoke (mezcla)
├── cancion__vocals.wav          # --preset all (individual)
├── cancion__drums.wav
├── cancion__bass.wav
├── cancion__guitar.wav
├── cancion__piano.wav
└── cancion__other.wav
```

---

## Archivos mezclados vs individuales

Algunos presets generan **un solo archivo** mezclando varios stems (ej: `karaoke`, `band`, `drums+bass`). Otros generan **un archivo por stem** (ej: `all`, `instrumental`). La diferencia está marcada en la tabla de presets como "1 archivo mezclado" vs "archivos individuales".

Con `--stems` o combinaciones libres con `+`, siempre se genera **un solo archivo mezclado**.

---

## Ejemplos

### Extraer solo la voz

```bash
python3.12 IA_audio_separator.py cancion.mp3 --preset vocals
# → audioseparate_cancion/cancion__vocals.wav
```

### Pista karaoke (todo sin voz en un solo archivo)

```bash
python3.12 IA_audio_separator.py cancion.mp3 --preset karaoke
# → audioseparate_cancion/cancion__karaoke.wav
```

### Los 6 stems por separado

```bash
python3.12 IA_audio_separator.py cancion.mp3 --preset all
# → 6 archivos: vocals, drums, bass, guitar, piano, other
```

### Separar desde video (extrae audio automáticamente)

```bash
python3.12 IA_audio_separator.py concierto.mp4 --preset vocals
python3.12 IA_audio_separator.py videoclip.mkv --preset all
```

### Combinación libre con `+` (un solo archivo mezclado)

```bash
# Voz + guitarra + piano mezclados en un archivo
python3.12 IA_audio_separator.py cancion.mp3 --preset vocals+guitar+piano

# Sección rítmica
python3.12 IA_audio_separator.py cancion.mp3 --preset drums+bass
```

### Stems manuales (uno o varios)

```bash
# Solo batería
python3.12 IA_audio_separator.py cancion.mp3 --stems drums

# Voz + piano + elementos no clasificados
python3.12 IA_audio_separator.py cancion.mp3 --stems vocals piano other
```

### Múltiples combos en un solo comando (`--combos`)

Genera todas las combinaciones pedidas en una sola ejecución. El modelo se carga una sola vez y se reutiliza para todos los combos, lo que es mucho más eficiente que ejecutar el script varias veces.

```bash
# Genera: vocals, drums+bass (mezclado) y los 6 stems individuales (all)
python3.12 IA_audio_separator.py cancion.mp3 --combos vocals drums+bass all

# Mezclas específicas para remixeo
python3.12 IA_audio_separator.py cancion.mp3 --combos vocals+guitar drums+bass+other karaoke

# Todo lo que puede necesitar un productor
python3.12 IA_audio_separator.py cancion.mp3 --combos all instrumental karaoke vocals
```

### Exportar como MP3 320k

```bash
python3.12 IA_audio_separator.py cancion.mp3 --preset all --mp3
# → genera archivos .mp3 en vez de .wav
```

### Carpeta de salida personalizada

```bash
python3.12 IA_audio_separator.py cancion.mp3 --preset all --output ./mis_stems/
```

### Usar GPU NVIDIA

```bash
python3.12 IA_audio_separator.py cancion.mp3 --preset all --device cuda
```

### Ver todos los presets disponibles

```bash
python3.12 IA_audio_separator.py --list-presets
```

---

## Cómo funciona

**Demucs** (`htdemucs_6s`) es un modelo de separación de fuentes de audio desarrollado por Meta AI. Usa una arquitectura híbrida encoder-decoder en dominio temporal y espectral para aislar cada instrumento del audio original.

El proceso interno por cada ejecución:

1. Si el archivo no es WAV o FLAC, ffmpeg lo convierte a WAV PCM 16-bit 44100 Hz estéreo en un temporal
2. El audio se resamplea automáticamente al sample rate del modelo si es diferente
3. Si el audio es mono se duplica a estéreo; si tiene más de 2 canales se recorta a los primeros 2
4. El modelo aplica la IA y genera los 6 stems en memoria
5. Se guardan solo los stems pedidos; si son varios y el preset lo indica, ffmpeg los mezcla en un único archivo con `amix`
6. Los archivos temporales se borran automáticamente

---

## Problemas conocidos

**Primera ejecución lenta** — descarga el modelo `htdemucs_6s` (~1 GB desde HuggingFace). A partir de la segunda ejecución el modelo se carga desde caché.

**CPU muy lento** — sin GPU, una canción de 4 minutos puede tardar 5-10 minutos. Usar `--device cuda` si se tiene GPU NVIDIA disponible.

**Error de ffmpeg al mezclar** — asegurarse de que ffmpeg está instalado con `sudo pacman -S ffmpeg`. Es necesario para los presets que generan un archivo mezclado (`karaoke`, `band`, `drums+bass`, etc.) y para exportar con `--mp3`.

**Audio en mono** — el script duplica el canal automáticamente para trabajar en estéreo internamente. La salida también será estéreo.

**Calidad variable según el género musical** — Demucs funciona mejor con música con instrumentos claramente diferenciados. Géneros con mucho procesamiento electrónico o voces muy distorsionadas pueden dar resultados menos limpios.
