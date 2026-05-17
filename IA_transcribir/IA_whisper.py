#!/usr/bin/env python3.12
import argparse
import logging
import os
import re
import subprocess
import sys
import tempfile
import warnings

# --- Supresión de avisos molestos ---
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*torchcodec.*")
logging.getLogger("lightning.pytorch").setLevel(logging.ERROR)
logging.getLogger("whisperx").setLevel(logging.ERROR)


def parse_args():
    epilog = """
═══════════════════════════════════════════════════════════════════
  EJEMPLOS DE USO
═══════════════════════════════════════════════════════════════════

  ── USO BÁSICO ──────────────────────────────────────────────────

  Transcripción rápida con detección automática de idioma:
    python IA_whisper.py video.mp4

  Especificar idioma español y guardar en carpeta personalizada:
    python IA_whisper.py podcast.mp3 -l es -o ./subtitulos/

  ── MODELOS ─────────────────────────────────────────────────────

  Modelo rápido (menos preciso, ideal para pruebas):
    python IA_whisper.py audio.mp3 -m tiny

  Modelo de máxima precisión (lento, recomendado para producción):
    python IA_whisper.py audio.mp3 -m large-v3

  ── FORMATO DE SALIDA ───────────────────────────────────────────

  Exportar solo en formato VTT (para web/HTML5):
    python IA_whisper.py audio.mp3 -f vtt

  Exportar solo en formato ASS (para editores de video avanzados):
    python IA_whisper.py audio.mp3 -f ass

  Exportar en todos los formatos a la vez (srt + vtt + ass):
    python IA_whisper.py audio.mp3 -f all

  ── SEGMENTACIÓN DE TEXTO ───────────────────────────────────────

  Máximo 4 palabras por línea de subtítulo (default: 2):
    python IA_whisper.py audio.mp3 --max-words 4

  Cortar subtítulo si hay 0.5s de silencio entre palabras:
    python IA_whisper.py audio.mp3 --max-silence 0.5

  Ambos combinados (4 palabras, corte a 0.3s de silencio):
    python IA_whisper.py audio.mp3 --max-words 4 --max-silence 0.3

  ── MAYÚSCULAS / MINÚSCULAS (--case) ────────────────────────────

  Todo el texto en MAYÚSCULAS (ideal para subtítulos de cine):
    python IA_whisper.py audio.mp3 --case upper
    → "hola mundo"  =>  "HOLA MUNDO"

  Todo el texto en minúsculas:
    python IA_whisper.py audio.mp3 --case lower
    → "HOLA MUNDO"  =>  "hola mundo"

  Title case - cada palabra empieza con mayúscula:
    python IA_whisper.py audio.mp3 --case title
    → "hola mundo"  =>  "Hola Mundo"

  Capitalize - solo la primera letra del segmento en mayúscula:
    python IA_whisper.py audio.mp3 --case capitalize
    → "hola mundo"  =>  "Hola mundo"

  Sin --case: el texto mantiene la capitalización que Whisper detecta.

  ── LIMPIEZA DE PUNTUACIÓN (--no-punctuation) ───────────────────

  Eliminar puntos, comas, signos de exclamación e interrogación:
    python IA_whisper.py audio.mp3 --no-punctuation ".,!?"

  Eliminar absolutamente toda la puntuación común:
    python IA_whisper.py audio.mp3 --no-punctuation all

  Combinar con mayúsculas (subtítulos limpios todo en caps):
    python IA_whisper.py audio.mp3 --no-punctuation all --case upper

  ── PRECISIÓN DE TRANSCRIPCIÓN ──────────────────────────────────

  Máxima precisión (beam grande, más paciente, más lento):
    python IA_whisper.py audio.mp3 --beam-size 10 --patience 2.0

  Modo rápido / ligero (menos exhaustivo):
    python IA_whisper.py audio.mp3 --beam-size 2 --patience 0.5

  Añadir algo de aleatoriedad para audios difíciles:
    python IA_whisper.py audio.mp3 --temperature 0.4

  Bajar el umbral de no-speech (menos segmentos descartados):
    python IA_whisper.py audio.mp3 --no-speech-threshold 0.3

  ── VAD (DETECCIÓN DE ACTIVIDAD DE VOZ) ─────────────────────────

  VAD más sensible (detecta voz más fácilmente):
    python IA_whisper.py audio.mp3 --vad-onset 0.3 --vad-offset 0.2

  VAD más estricto (ignora sonidos débiles):
    python IA_whisper.py audio.mp3 --vad-onset 0.7 --vad-offset 0.5

  ── GPU / RENDIMIENTO ───────────────────────────────────────────

  Usar GPU NVIDIA con precisión float16 (más rápido):
    python IA_whisper.py audio.mp3 --device cuda --compute-type float16

  Usar GPU con int8 (más rápido aún, algo menos preciso):
    python IA_whisper.py audio.mp3 --device cuda --compute-type int8

  CPU con int8 (más rápido que float32 en CPU):
    python IA_whisper.py audio.mp3 --compute-type int8

  ── DIARIZACIÓN (IDENTIFICAR HABLANTES) ─────────────────────────

  Activar diarización (requiere token de HuggingFace):
    python IA_whisper.py audio.mp3 --diarize --hf-token TU_TOKEN_AQUI

  Con diarización + modelo grande + GPU:
    python IA_whisper.py reunion.mp3 --diarize --hf-token TOKEN
      --device cuda --compute-type float16 -m large-v3

  ── COMBINACIONES TÍPICAS DE PRODUCCIÓN ─────────────────────────

  Subtítulos para YouTube (español, limpio, 3 palabras/línea):
    python IA_whisper.py video.mp4 -l es -m large-v3
      --max-words 3 --no-punctuation ".,!?¡¿" --case capitalize

  Subtítulos estilo cine (inglés, mayúsculas, sin puntuación):
    python IA_whisper.py film.mp4 -l en -m large-v3
      --case upper --no-punctuation all -f ass

  Transcripción rápida para revisión (modelo tiny, formato vtt):
    python IA_whisper.py borrador.mp3 -m tiny -f vtt -o ./draft/

  Máxima calidad con GPU y todos los formatos:
    python IA_whisper.py master.wav -l es -m large-v3
      --device cuda --compute-type float16
      --beam-size 10 --patience 2.0
      --max-words 3 --case capitalize -f all -o ./final/

═══════════════════════════════════════════════════════════════════
"""

    parser = argparse.ArgumentParser(
        description=(
            "WhisperX Ultra-Pro: Transcripción, sincronización y limpieza de subtítulos.\n"
            "Convierte audio/video a subtítulos precisos con timestamps por palabra."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
        add_help=False,
    )

    # ── Requeridos ──────────────────────────────────────────────────────────
    parser.add_argument(
        "input",
        help="Archivo de audio o video de entrada (mp3, mp4, wav, mkv, etc.).",
    )

    # ── Opciones principales ─────────────────────────────────────────────────
    grp_main = parser.add_argument_group("OPCIONES PRINCIPALES")
    grp_main.add_argument(
        "-l", "--language", default=None,
        metavar="CÓDIGO",
        help=(
            "Código de idioma ISO 639-1 para la transcripción. "
            "Ejemplos: 'es' (español), 'en' (inglés), 'fr' (francés), 'pt' (portugués). "
            "Si se omite, WhisperX detecta el idioma automáticamente. "
            "(Default: auto-detección)"
        ),
    )
    grp_main.add_argument(
        "-m", "--model", default="medium",
        metavar="NOMBRE",
        help=(
            "Modelo Whisper a usar. Más grande = más preciso pero más lento y más RAM. "
            "Opciones: tiny (39M), base (74M), small (244M), medium (769M), "
            "large-v1, large-v2, large-v3 (1550M). "
            "(Default: medium)"
        ),
    )
    grp_main.add_argument(
        "-f", "--format", default="srt",
        choices=["srt", "vtt", "ass", "all"],
        help=(
            "Formato de salida de los subtítulos. "
            "'srt': SubRip, el más compatible (reproductores, YouTube, etc.). "
            "'vtt': WebVTT, para web/HTML5. "
            "'ass': SubStation Alpha, para editores de video avanzados (Aegisub, etc.). "
            "'all': genera los tres formatos simultáneamente. "
            "(Default: srt)"
        ),
    )
    grp_main.add_argument(
        "-o", "--output-dir", default="./subs/",
        metavar="CARPETA",
        help=(
            "Carpeta donde se guardarán los archivos de subtítulos generados. "
            "Se crea automáticamente si no existe. "
            "(Default: ./subs/)"
        ),
    )

    # ── Segmentación ─────────────────────────────────────────────────────────
    grp_seg = parser.add_argument_group("SEGMENTACIÓN DE TEXTO")
    grp_seg.add_argument(
        "--max-words", type=int, default=2,
        metavar="N",
        help=(
            "Número máximo de palabras por línea de subtítulo. "
            "Valores bajos (1-2) son ideales para karaoke o ritmo rápido. "
            "Valores altos (4-6) son mejores para subtítulos de diálogo normal. "
            "(Default: 2)"
        ),
    )
    grp_seg.add_argument(
        "--max-silence", type=float, default=0.1,
        metavar="SEG",
        help=(
            "Tiempo de silencio en segundos que fuerza un corte entre subtítulos. "
            "Valores pequeños (0.1) crean más cortes y subtítulos más cortos. "
            "Valores grandes (0.5-1.0) agrupan más palabras en el mismo subtítulo. "
            "(Default: 0.1)"
        ),
    )

    # ── Transformación de texto ───────────────────────────────────────────────
    grp_txt = parser.add_argument_group("TRANSFORMACIÓN DE TEXTO")
    grp_txt.add_argument(
        "--case", default=None,
        choices=["upper", "lower", "title", "capitalize"],
        help=(
            "Transforma las mayúsculas/minúsculas del texto transcrito. "
            "'upper': TODO EL TEXTO EN MAYÚSCULAS (ej: subtítulos estilo cine). "
            "'lower': todo el texto en minúsculas. "
            "'title': Cada Palabra Empieza Con Mayúscula. "
            "'capitalize': Solo la primera letra de cada segmento en mayúscula. "
            "Si se omite, el texto conserva la capitalización original de Whisper. "
            "(Default: sin cambios)"
        ),
    )
    grp_txt.add_argument(
        "--no-punctuation", default=None,
        metavar="CHARS",
        help=(
            "Elimina los caracteres de puntuación indicados del texto final. "
            "Pasar los caracteres entre comillas sin espacios: '.,!?' "
            "Usar el valor especial 'all' para eliminar toda la puntuación común "
            "( . , ! ? ¡ ¿ ; : \" ( ) [ ] { } ). "
            "(Default: no eliminar nada)"
        ),
    )

    # ── Precisión de transcripción ────────────────────────────────────────────
    grp_prec = parser.add_argument_group("PRECISIÓN DE TRANSCRIPCIÓN")
    grp_prec.add_argument(
        "--beam-size", type=int, default=5,
        metavar="N",
        help=(
            "Número de hipótesis que el modelo evalúa en paralelo (beam search). "
            "Mayor valor = más preciso pero más lento y más memoria. "
            "Rango recomendado: 1 (greedy rápido) a 10 (exhaustivo). "
            "(Default: 5)"
        ),
    )
    grp_prec.add_argument(
        "--patience", type=float, default=1.0,
        metavar="N",
        help=(
            "Factor de paciencia del beam search. Multiplica el número máximo de "
            "candidatos evaluados. Mayor valor = más exhaustivo, más lento. "
            "(Default: 1.0)"
        ),
    )
    grp_prec.add_argument(
        "--temperature", type=float, default=0.0,
        metavar="N",
        help=(
            "Temperatura de muestreo del modelo. "
            "0.0 = modo greedy (determinista, más consistente). "
            "0.2-0.8 = introduce aleatoriedad, útil para audios ambiguos o ruidosos. "
            "(Default: 0.0)"
        ),
    )
    grp_prec.add_argument(
        "--word-timestamps", action="store_true", default=True,
        help=(
            "Fuerza la generación de timestamps individuales por palabra. "
            "Necesario para la sincronización fina. Siempre activado internamente. "
            "(Default: activado)"
        ),
    )
    grp_prec.add_argument(
        "--condition-on-prev", action="store_true", default=True,
        help=(
            "El modelo usa el segmento anterior como contexto para mejorar la coherencia "
            "del texto transcrito. Puede causar alucinaciones en audios muy ruidosos. "
            "(Default: activado)"
        ),
    )
    grp_prec.add_argument(
        "--no-speech-threshold", type=float, default=0.6,
        metavar="N",
        help=(
            "Umbral de probabilidad para descartar segmentos sin voz. "
            "Rango: 0.0 a 1.0. Valores altos (0.8+) descartan más segmentos dudosos. "
            "Valores bajos (0.3) conservan casi todo, incluido ruido de fondo. "
            "(Default: 0.6)"
        ),
    )
    grp_prec.add_argument(
        "--compression-ratio-threshold", type=float, default=2.4,
        metavar="N",
        help=(
            "Umbral para detectar segmentos con posibles alucinaciones del modelo. "
            "Un ratio muy alto indica texto repetitivo o sin sentido. "
            "Valores típicos: 1.8 (estricto) a 3.0 (permisivo). "
            "(Default: 2.4)"
        ),
    )

    # ── VAD ──────────────────────────────────────────────────────────────────
    grp_vad = parser.add_argument_group("VAD - DETECCIÓN DE ACTIVIDAD DE VOZ")
    grp_vad.add_argument(
        "--vad-filter", action="store_true", default=True,
        help=(
            "Activa el filtro VAD (Voice Activity Detection) para ignorar silencios "
            "y ruido de fondo antes de transcribir. Mejora la velocidad y precisión. "
            "(Default: activado)"
        ),
    )
    grp_vad.add_argument(
        "--vad-onset", type=float, default=0.500,
        metavar="N",
        help=(
            "Umbral de probabilidad para considerar que comienza la voz. "
            "Rango: 0.0 a 1.0. Valores bajos (0.3) detectan voz más fácilmente. "
            "Valores altos (0.7) requieren mayor certeza antes de activar. "
            "(Default: 0.500)"
        ),
    )
    grp_vad.add_argument(
        "--vad-offset", type=float, default=0.363,
        metavar="N",
        help=(
            "Umbral de probabilidad para considerar que termina la voz. "
            "Debe ser menor que --vad-onset. Valores bajos mantienen la voz activa "
            "por más tiempo antes de considerar que terminó. "
            "(Default: 0.363)"
        ),
    )

    # ── Hardware ─────────────────────────────────────────────────────────────
    grp_hw = parser.add_argument_group("HARDWARE Y RENDIMIENTO")
    grp_hw.add_argument(
        "--device", default="cpu", choices=["cpu", "cuda"],
        help=(
            "Dispositivo de cómputo para ejecutar el modelo. "
            "'cpu': compatible con cualquier máquina, más lento. "
            "'cuda': GPU NVIDIA con CUDA, mucho más rápido (requiere torch+cuda). "
            "(Default: cpu)"
        ),
    )
    grp_hw.add_argument(
        "--compute-type", default="float32",
        metavar="TIPO",
        help=(
            "Precisión numérica del modelo. Afecta velocidad y uso de VRAM/RAM. "
            "'float32': máxima precisión, para CPU. "
            "'float16': mitad de VRAM, muy rápido en GPU. "
            "'int8': mínimo uso de memoria, más rápido aún (ligera pérdida de calidad). "
            "(Default: float32)"
        ),
    )

    # ── Diarización ──────────────────────────────────────────────────────────
    grp_diar = parser.add_argument_group("DIARIZACIÓN DE HABLANTES")
    grp_diar.add_argument(
        "--diarize", action="store_true",
        help=(
            "Activa la diarización: identifica y etiqueta quién habla en cada segmento "
            "(SPK_0, SPK_1, etc.). Requiere --hf-token. "
            "Aumenta significativamente el tiempo de procesamiento."
        ),
    )
    grp_diar.add_argument(
        "--hf-token", default=None,
        metavar="TOKEN",
        help=(
            "Token de acceso de HuggingFace, necesario para descargar el modelo de "
            "diarización (pyannote/speaker-diarization). "
            "Obtenerlo en: https://huggingface.co/settings/tokens "
            "(Default: None)"
        ),
    )

    # ── Ayuda ────────────────────────────────────────────────────────────────
    parser.add_argument("--help", action="help", help="Mostrar esta ayuda y salir.")

    return parser.parse_args()


def print_menu(args):
    print("\n" + "═" * 65)
    print("  WHISPERX PRO - CONFIGURACIÓN DE PROCESAMIENTO")
    print("═" * 65)

    defaults = {
        "model": "medium", "max_words": 2, "max_silence": 0.1,
        "format": "srt", "output_dir": "./subs/", "device": "cpu",
        "compute_type": "float32", "beam_size": 5, "patience": 1.0,
        "temperature": 0.0, "no_speech_threshold": 0.6,
        "compression_ratio_threshold": 2.4,
        "vad_onset": 0.500, "vad_offset": 0.363,
    }

    def tag(key, val): return "DEFAULT" if val == defaults.get(key) else "ESPECIFICADO"

    config = [
        ("Entrada",          os.path.basename(args.input),                      "ESPECIFICADO"),
        ("Modelo",           args.model,                                         tag("model", args.model)),
        ("Idioma",           args.language or "Auto-detect",                    "ESPECIFICADO" if args.language else "DEFAULT"),
        ("Máx. Palabras",    args.max_words,                                     tag("max_words", args.max_words)),
        ("Corte Silencio",   f"{args.max_silence}s",                            tag("max_silence", args.max_silence)),
        ("Formato",          args.format.upper(),                                tag("format", args.format)),
        ("Destino",          args.output_dir,                                    tag("output_dir", args.output_dir)),
        ("Dispositivo",      args.device.upper(),                                tag("device", args.device)),
        ("Precisión",        args.compute_type,                                  tag("compute_type", args.compute_type)),
        ("─── PRECISIÓN ──", "─" * 25,                                          "─────────"),
        ("Beam Size",        args.beam_size,                                     tag("beam_size", args.beam_size)),
        ("Patience",         args.patience,                                      tag("patience", args.patience)),
        ("Temperature",      args.temperature,                                   tag("temperature", args.temperature)),
        ("No-Speech Thresh", args.no_speech_threshold,                          tag("no_speech_threshold", args.no_speech_threshold)),
        ("Comp.Ratio Thresh",args.compression_ratio_threshold,                  tag("compression_ratio_threshold", args.compression_ratio_threshold)),
        ("VAD Filter",       "Activado" if args.vad_filter else "Desactivado",  tag("vad_onset", args.vad_onset)),
        ("VAD Onset",        args.vad_onset,                                     tag("vad_onset", args.vad_onset)),
        ("VAD Offset",       args.vad_offset,                                    tag("vad_offset", args.vad_offset)),
        ("─── EXTRA ─────", "─" * 25,                                           "─────────"),
        ("Limpiar puntuación", args.no_punctuation or "Ninguna",               "ESPECIFICADO" if args.no_punctuation else "DEFAULT"),
        ("Transformación texto", args.case or "Sin cambios",                   "ESPECIFICADO" if args.case else "DEFAULT"),
        ("Diarización",      "Activada" if args.diarize else "Desactivada",    "ESPECIFICADO" if args.diarize else "DEFAULT"),
    ]

    for label, value, status in config:
        print(f"  {label:<22} : {str(value):<22} [{status}]")

    print("═" * 65 + "\n")


def clean_text(text, chars_to_remove):
    if not chars_to_remove:
        return text
    if chars_to_remove.lower() == "all":
        chars_to_remove = '.,!?¡¿;:"()[]{}'
    pattern = "[" + re.escape(chars_to_remove) + "]"
    # Limpiar caracteres y normalizar espacios múltiples
    cleaned = re.sub(pattern, "", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def normalize_text(text):
    """Normaliza el texto: espacios antes de signos de puntuación y capitalización."""
    # Eliminar espacios antes de puntuación
    text = re.sub(r"\s([.,!?;:])", r"\1", text)
    # Capitalizar primera letra
    if text:
        text = text[0].upper() + text[1:]
    return text.strip()


def apply_case(text, case_mode):
    """Aplica transformación de mayúsculas/minúsculas al texto."""
    if case_mode is None:
        return text
    if case_mode == "upper":
        return text.upper()
    if case_mode == "lower":
        return text.lower()
    if case_mode == "title":
        return text.title()
    if case_mode == "capitalize":
        return text.capitalize()
    return text



    """Convierte el audio a WAV 16kHz mono PCM para máxima compatibilidad con WhisperX."""
    tmp = tempfile.NamedTemporaryFile(suffix="_clean_16k.wav", delete=False)
    tmp.close()
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", input_path,
            "-ar", "16000",   # 16kHz requerido por Whisper
            "-ac", "1",       # mono
            "-c:a", "pcm_s16le",
            "-af", "highpass=f=80,lowpass=f=8000",  # filtro de banda para voz
            tmp.name,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return tmp.name


def format_time_srt(seconds):
    seconds = max(0.0, seconds)
    h, m = divmod(int(seconds), 3600)
    m, s = divmod(m, 60)
    ms = int(round((seconds % 1) * 1000))
    ms = min(ms, 999)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_time_vtt(seconds):
    """Formato para WebVTT (usa punto en lugar de coma)."""
    return format_time_srt(seconds).replace(",", ".")


def format_time_ass(seconds):
    """Formato para SubStation Alpha."""
    seconds = max(0.0, seconds)
    h, m = divmod(int(seconds), 3600)
    m, s = divmod(m, 60)
    cs = int(round((seconds % 1) * 100))  # centésimas
    cs = min(cs, 99)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def build_final_segments(result, args):
    """
    Agrupa las palabras en segmentos según max_words y max_silence.
    Maneja palabras sin timestamp de forma más robusta.
    """
    final_segments = []

    for seg in result["segments"]:
        words = seg.get("words", [])
        if not words:
            # Segmento sin palabras individuales: usar tiempos del segmento completo
            raw_text = seg.get("text", "").strip()
            clean_txt = clean_text(raw_text, args.no_punctuation)
            clean_txt = normalize_text(clean_txt)
            clean_txt = apply_case(clean_txt, args.case)
            if clean_txt and "start" in seg and "end" in seg:
                final_segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": clean_txt,
                    "speaker": seg.get("speaker", "SPK"),
                })
            continue

        # Separar palabras con y sin timestamp
        timed_words = []
        last_end = seg.get("start", 0.0)

        for i, w in enumerate(words):
            if "start" in w and "end" in w:
                timed_words.append(w)
                last_end = w["end"]
            else:
                # Interpolar timestamp para palabras sin timing
                word_text = w.get("word", "").strip()
                if not word_text:
                    continue
                # Estimar duración proporcional al largo de la palabra
                char_count = len(word_text)
                estimated_duration = max(0.1, char_count * 0.07)
                timed_words.append({
                    "word": word_text,
                    "start": last_end,
                    "end": last_end + estimated_duration,
                    "score": w.get("score", 0.0),
                    "_interpolated": True,
                })
                last_end += estimated_duration

        if not timed_words:
            continue

        # Agrupar en chunks
        chunk = []
        for i, w in enumerate(timed_words):
            chunk.append(w)
            cut = False

            if len(chunk) >= args.max_words:
                cut = True
            elif i + 1 < len(timed_words):
                gap = timed_words[i + 1]["start"] - w["end"]
                if gap > args.max_silence:
                    cut = True

            if cut or i == len(timed_words) - 1:
                raw_text = " ".join(cw["word"] for cw in chunk).strip()
                clean_txt = clean_text(raw_text, args.no_punctuation)
                clean_txt = normalize_text(clean_txt)
                clean_txt = apply_case(clean_txt, args.case)

                if clean_txt:
                    # Calcular score promedio de confianza (si está disponible)
                    scores = [cw.get("score", None) for cw in chunk if cw.get("score") is not None]
                    avg_score = round(sum(scores) / len(scores), 3) if scores else None

                    final_segments.append({
                        "start": chunk[0]["start"],
                        "end": chunk[-1]["end"],
                        "text": clean_txt,
                        "speaker": seg.get("speaker", "SPK"),
                        "confidence": avg_score,
                        "has_interpolated": any(cw.get("_interpolated") for cw in chunk),
                    })
                chunk = []

    return final_segments


def write_srt(segments, path, diarize):
    with open(path, "w", encoding="utf-8") as f:
        for idx, s in enumerate(segments, 1):
            spk = f"[{s['speaker']}] " if diarize else ""
            f.write(f"{idx}\n")
            f.write(f"{format_time_srt(s['start'])} --> {format_time_srt(s['end'])}\n")
            f.write(f"{spk}{s['text']}\n\n")
    print(f"  [✓] SRT  -> {path}")


def write_vtt(segments, path, diarize):
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for idx, s in enumerate(segments, 1):
            spk = f"<v {s['speaker']}>" if diarize else ""
            f.write(f"{idx}\n")
            f.write(f"{format_time_vtt(s['start'])} --> {format_time_vtt(s['end'])}\n")
            f.write(f"{spk}{s['text']}\n\n")
    print(f"  [✓] VTT  -> {path}")


def write_ass(segments, path, diarize):
    """Exporta a formato ASS (SubStation Alpha) con estilo básico."""
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1920\n"
        "PlayResY: 1080\n"
        "WrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
        "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
        "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
        "Alignment,MarginL,MarginR,MarginV,Encoding\n"
        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,"
        "&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,50,1\n\n"
        "[Events]\n"
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        for s in segments:
            spk = s["speaker"] if diarize else "Default"
            text = s["text"].replace("\n", "\\N")
            f.write(
                f"Dialogue: 0,{format_time_ass(s['start'])},{format_time_ass(s['end'])},"
                f"Default,{spk},0,0,0,,{text}\n"
            )
    print(f"  [✓] ASS  -> {path}")


def write_confidence_report(segments, path):
    """Genera un reporte de confianza por segmento (útil para revisar palabras dudosas)."""
    low_confidence = [s for s in segments if s.get("confidence") is not None and s["confidence"] < 0.7]
    interpolated = [s for s in segments if s.get("has_interpolated")]

    with open(path, "w", encoding="utf-8") as f:
        f.write("REPORTE DE CONFIANZA - WhisperX Pro\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total segmentos: {len(segments)}\n")
        f.write(f"Segmentos con baja confianza (<0.70): {len(low_confidence)}\n")
        f.write(f"Segmentos con timestamps interpolados: {len(interpolated)}\n\n")

        if low_confidence:
            f.write("─── SEGMENTOS DE BAJA CONFIANZA ───\n")
            for s in low_confidence:
                t = format_time_srt(s["start"])
                f.write(f"  [{t}] (score: {s['confidence']}) {s['text']}\n")
            f.write("\n")

        if interpolated:
            f.write("─── SEGMENTOS CON TIMING INTERPOLADO ───\n")
            for s in interpolated:
                t = format_time_srt(s["start"])
                f.write(f"  [{t}] {s['text']}\n")

    if low_confidence or interpolated:
        print(f"  [!] Reporte de confianza -> {path}")


def run_main():
    args = parse_args()
    print_menu(args)

    import whisperx

    # 1. Convertir audio
    print("[*] Preparando audio...")
    audio_tmp = convert_audio(args.input)

    try:
        # 2. Cargar modelo
        print("[*] Iniciando motor de IA...")
        model = whisperx.load_model(
            args.model,
            args.device,
            compute_type=args.compute_type,
            language=args.language,
            asr_options={
                "beam_size": args.beam_size,
                "patience": args.patience,
                "temperatures": [args.temperature] if args.temperature == 0.0 else [args.temperature, 0.2, 0.4, 0.6, 0.8, 1.0],
                "compression_ratio_threshold": args.compression_ratio_threshold,
                "no_speech_threshold": args.no_speech_threshold,
                "condition_on_previous_text": args.condition_on_prev,
                "word_timestamps": True,  # Siempre forzar timestamps por palabra
            },
            vad_options={
                "vad_onset": args.vad_onset,
                "vad_offset": args.vad_offset,
            } if args.vad_filter else None,
        )

        audio = whisperx.load_audio(audio_tmp)

        # 3. Transcribir
        print("[*] Transcribiendo contenido...")
        result = model.transcribe(
            audio,
            batch_size=16,
            language=args.language,
            print_progress=False,
        )
        detected_lang = result.get("language", args.language or "?")
        print(f"    → Idioma detectado: {detected_lang.upper()}")
        print(f"    → Segmentos crudos: {len(result.get('segments', []))}")

        # 4. Alineación
        print("[*] Ajustando sincronización milimétrica...")
        model_a, metadata = whisperx.load_align_model(
            language_code=result["language"],
            device=args.device,
        )
        result = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio,
            args.device,
            return_char_alignments=False,
        )

        # 5. Diarización (opcional)
        if args.diarize:
            if not args.hf_token:
                print("[!] AVISO: --hf-token requerido para diarización. Omitiendo.")
            else:
                print("[*] Identificando hablantes...")
                diarize_model = whisperx.DiarizationPipeline(
                    use_auth_token=args.hf_token,
                    device=args.device,
                )
                diarize_segments = diarize_model(audio)
                result = whisperx.assign_word_speakers(diarize_segments, result)

        # 6. Construir segmentos finales
        print("[*] Construyendo segmentos finales...")
        final_segments = build_final_segments(result, args)
        print(f"    → Segmentos exportados: {len(final_segments)}")

        # 7. Exportar
        os.makedirs(args.output_dir, exist_ok=True)
        base = os.path.join(
            args.output_dir,
            os.path.splitext(os.path.basename(args.input))[0],
        )

        print("\n[*] Exportando archivos...")
        fmt = args.format.lower()
        if fmt in ("srt", "all"):
            write_srt(final_segments, f"{base}.srt", args.diarize)
        if fmt in ("vtt", "all"):
            write_vtt(final_segments, f"{base}.vtt", args.diarize)
        if fmt in ("ass", "all"):
            write_ass(final_segments, f"{base}.ass", args.diarize)

        # 8. Reporte de confianza
        write_confidence_report(final_segments, f"{base}_confidence.txt")

        print(f"\n[✓] ÉXITO: Subtítulos generados en -> {args.output_dir}")

    except FileNotFoundError:
        print("\n[!] ERROR: No se encontró el archivo de entrada.")
    except subprocess.CalledProcessError:
        print("\n[!] ERROR: Falló la conversión de audio. ¿Está instalado ffmpeg?")
    except Exception as e:
        print(f"\n[!] ERROR: {str(e)}")
        raise
    finally:
        if os.path.exists(audio_tmp):
            os.unlink(audio_tmp)

    print("\n[!] Proceso finalizado.\n")


if __name__ == "__main__":
    run_main()
