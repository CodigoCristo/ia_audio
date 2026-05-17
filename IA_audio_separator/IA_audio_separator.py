#!/usr/bin/env python3
"""
IA_audio_separator.py
=====================
Separador de audio/video con IA usando Demucs (Meta AI) - htdemucs_6s
Stems disponibles: vocals, drums, bass, guitar, piano, other

Soporta audio: mp3, wav, flac, ogg, m4a, aac, opus, wma
Soporta video: mp4, mkv, avi, mov, webm, m4v, ts, mts  (extrae audio con ffmpeg)
"""

import argparse
import sys
import time
import tempfile
import shutil
import subprocess
import warnings
from pathlib import Path

# Suprimir warnings de deprecacion de torchaudio (ruido visual innecesario)
warnings.filterwarnings("ignore", category=UserWarning, module="torchaudio")

# ─────────────────────────────────────────────────────────────
#  EXTENSIONES SOPORTADAS
# ─────────────────────────────────────────────────────────────
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wma", ".aiff"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts", ".mts", ".mpeg", ".mpg", ".wmv"}

# ─────────────────────────────────────────────────────────────
#  PRESETS
# ─────────────────────────────────────────────────────────────
PRESETS: dict[str, dict] = {
    # Voz
    "vocals":         {"stems": ["vocals"],                                    "desc": "Solo voz",                        "cat": "Voz"},
    "vocals+guitar":  {"stems": ["vocals", "guitar"],                          "desc": "Voz + Guitarra",                  "cat": "Voz"},
    "vocals+piano":   {"stems": ["vocals", "piano"],                           "desc": "Voz + Piano",                     "cat": "Voz"},
    "vocals+bass":    {"stems": ["vocals", "bass"],                            "desc": "Voz + Bajo",                      "cat": "Voz"},
    # Ritmo
    "drums":          {"stems": ["drums"],                                     "desc": "Solo bateria",                    "cat": "Ritmo"},
    "bass":           {"stems": ["bass"],                                      "desc": "Solo bajo",                       "cat": "Ritmo"},
    "drums+bass":     {"stems": ["drums", "bass"],                             "desc": "Bateria + Bajo (seccion ritmica)", "cat": "Ritmo"},
    # Melodia
    "guitar":         {"stems": ["guitar"],                                    "desc": "Solo guitarra",                   "cat": "Melodia"},
    "piano":          {"stems": ["piano"],                                     "desc": "Solo piano",                      "cat": "Melodia"},
    "guitar+piano":   {"stems": ["guitar", "piano"],                           "desc": "Guitarra + Piano",                "cat": "Melodia"},
    # Mezclas
    "band":           {"stems": ["drums", "bass", "guitar"],                   "desc": "Banda: Bateria + Bajo + Guitarra (archivo unico)", "cat": "Mezclas"},
    "instrumental":   {"stems": ["drums", "bass", "guitar", "piano", "other"],"desc": "Todo sin voz, cada stem por separado",             "cat": "Mezclas", "individual": True},
    "karaoke":        {"stems": ["drums", "bass", "guitar", "piano", "other"],"desc": "Pista karaoke: un solo archivo sin voz (drums+bass+guitar+piano+other)", "cat": "Mezclas"},
    "other":          {"stems": ["other"],                                     "desc": "Elementos no clasificados",                        "cat": "Mezclas"},
    # Todo
    "all":            {"stems": ["vocals", "drums", "bass", "guitar", "piano", "other"], "desc": "Los 6 stems cada uno por separado", "cat": "Completo", "individual": True},
}

VALID_STEMS = ["vocals", "drums", "bass", "guitar", "piano", "other"]
MODEL = "htdemucs_6s"

def slug_from_name(path: Path, max_words: int = 2) -> str:
    """
    Genera un slug limpio desde el nombre del archivo.
    Toma las primeras palabras significativas (ignorando brackets, IDs, numeros).
    Ej: Green Day - Basket Case (Lyrics) [_lof1pYtL9Q] -> green_day
    Ej: 04 - Hey Jude                                   -> hey_jude
    """
    import re
    name = path.stem
    name = re.sub(r"[\[(][^\])]*[\])]", "", name)
    for pfx in ("_tmp_", "_audio_", "_video_audio_"):
        if name.startswith(pfx):
            name = name[len(pfx):]
            break
    tokens = re.split(r"[\s\-_.]+" , name)
    words = [t.lower() for t in tokens
             if re.match(r"^[a-zA-Z\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1"                          r"\u00c1\u00c9\u00cd\u00d3\u00da\u00dc\u00d1]{2,}$", t)]
    chosen = words[:max_words] if words else ["audio"]
    return "_".join(chosen)

# ─────────────────────────────────────────────────────────────
#  CONSOLA
# ─────────────────────────────────────────────────────────────
def color(text, code): return f"\033[{code}m{text}\033[0m"
def info(m):    print(color(f"  i  {m}", "94"))
def success(m): print(color(f"  v  {m}", "92"))
def warn(m):    print(color(f"  !  {m}", "93"))
def error(m):   print(color(f"  x  {m}", "91"), file=sys.stderr)
def header(m):  print(color(f"\n{'─'*58}\n  {m}\n{'─'*58}", "96"))
def dim(m):     return color(m, "90")

# ─────────────────────────────────────────────────────────────
#  DEPENDENCIAS
# ─────────────────────────────────────────────────────────────
def check_dependencies() -> bool:
    try:
        import torch      # noqa: F401
        import torchaudio # noqa: F401
        import demucs     # noqa: F401
        return True
    except ImportError as e:
        error(f"Dependencia faltante: {e}")
        print("\n  Instala con:")
        print(color("  python3.12 -m pip install demucs torch torchaudio", "93"))
        return False

def check_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def require_ffmpeg(action: str):
    if not check_ffmpeg():
        error(f"ffmpeg requerido para {action}.")
        print("  Linux : sudo apt install ffmpeg")
        print("  macOS : brew install ffmpeg")
        print("  Windows: https://ffmpeg.org/download.html")
        sys.exit(1)

# ─────────────────────────────────────────────────────────────
#  TIPO DE ARCHIVO
# ─────────────────────────────────────────────────────────────

# soundfile (backend de torchaudio) solo lee WAV y FLAC de forma nativa.
# Todo lo demas (m4a, mp3, aac, ogg, opus, wma, video, etc.) necesita ffmpeg.
NATIVE_EXTS = {".wav", ".flac"}

def file_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in AUDIO_EXTS: return "audio"
    if ext in VIDEO_EXTS: return "video"
    return "unknown"

def needs_conversion(path: Path) -> bool:
    """True si torchaudio/soundfile no puede leer el archivo directamente."""
    return path.suffix.lower() not in NATIVE_EXTS

# ─────────────────────────────────────────────────────────────
#  CONVERTIR CUALQUIER AUDIO/VIDEO -> WAV TEMPORAL con ffmpeg
# ─────────────────────────────────────────────────────────────
def convert_to_wav(src: Path, tmp_dir: Path) -> Path:
    """
    Convierte cualquier audio o video a WAV PCM 16-bit 44100 Hz stereo.
    Usado para: video (mp4, mkv...) Y audio no nativo (m4a, mp3, aac, ogg, opus, wma...).
    El archivo temporal se borra automaticamente al terminar el proceso.
    """
    require_ffmpeg(f"convertir {src.suffix}")
    tmp_wav = tmp_dir / f"_tmp_{src.stem}.wav"

    if file_type(src) == "video":
        info(f"Video detectado: extrayendo audio de {src.name}")
    else:
        info(f"Formato {src.suffix} no nativo: convirtiendo a WAV con ffmpeg")
    info(f"Temporal: {tmp_wav.name}")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-vn",                  # ignorar pista de video si existe
        "-acodec", "pcm_s16le", # WAV sin comprimir
        "-ar", "44100",         # 44.1 kHz
        "-ac", "2",             # stereo
        str(tmp_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        error(f"ffmpeg fallo al convertir {src.name}:")
        lines = [l for l in result.stderr.splitlines() if l.strip()]
        print(color("\n".join(lines[-6:]), "91"))
        sys.exit(1)

    size_kb = tmp_wav.stat().st_size // 1024
    success(f"Listo: {size_kb:,} KB  ->  {tmp_wav.name}")
    return tmp_wav

# ─────────────────────────────────────────────────────────────
#  SEPARACION
# ─────────────────────────────────────────────────────────────
def separate(
    input_file: Path,
    stems: list[str],
    output_dir: Path,
    device: str,
    mp3: bool,
    label: str = "",
    mix_output: bool = False,
) -> list[Path]:
    import torch
    import torchaudio
    from demucs.pretrained import get_model
    from demucs.apply import apply_model

    tag = f"[{label}] " if label else ""
    header(f"Separando {tag}: {input_file.name}")
    info(f"Stems    : {', '.join(stems)}")
    info(f"Salida   : {output_dir}")
    info(f"Dispositivo: {device}")
    print()

    # Modelo
    info("Cargando modelo Demucs (primera vez descarga ~1 GB)...")
    t0 = time.time()
    model = get_model(MODEL)
    model.to(device)
    model.eval()
    success(f"Modelo listo en {time.time()-t0:.1f}s")

    # Audio
    info("Leyendo audio...")
    wav, sr = torchaudio.load(str(input_file))

    if sr != model.samplerate:
        info(f"Resampleando {sr} Hz -> {model.samplerate} Hz")
        wav = torchaudio.functional.resample(wav, sr, model.samplerate)

    # Asegurar stereo
    if wav.shape[0] == 1:
        wav = wav.repeat(2, 1)
    elif wav.shape[0] > 2:
        wav = wav[:2]

    wav = wav.to(device)
    ref = wav.mean(0)
    wav_norm = (wav - ref.mean()) / (ref.std() + 1e-8)

    # IA
    info("Procesando con IA... (puede tardar segun duracion del archivo)")
    t1 = time.time()
    with torch.no_grad():
        sources = apply_model(model, wav_norm[None], device=device)[0]
    sources = sources * (ref.std() + 1e-8) + ref.mean()
    success(f"IA completada en {time.time()-t1:.1f}s")

    # Guardar
    output_dir.mkdir(parents=True, exist_ok=True)

    # Limpiar nombre base (quitar cualquier prefijo temporal)
    base_name = input_file.stem
    for pfx in ("_tmp_", "_audio_", "_video_audio_"):
        if base_name.startswith(pfx):
            base_name = base_name[len(pfx):]
            break

    suffix = f"__{label}" if label else ""
    saved: list[Path] = []

    # Recolectar audios de los stems pedidos
    stem_audios: list[tuple[str, object]] = []
    for i, stem_name in enumerate(model.sources):
        if stem_name not in stems:
            continue
        stem_audios.append((stem_name, sources[i].cpu()))

    if mix_output and len(stem_audios) > 1:
        # ── Mezclar todos los stems en un solo archivo ──
        require_ffmpeg("mezclar stems en un archivo")
        ext        = "mp3" if mp3 else "wav"
        # Usar el label del preset (ej: "karaoke") como nombre, no los stems individuales
        mix_name   = label if label else "+".join(s for s, _ in stem_audios)
        final_name = f"{base_name}__{mix_name}.{ext}"
        out_path   = output_dir / final_name

        # Guardar cada stem como WAV temporal
        tmp_wavs: list[Path] = []
        for stem_name, audio in stem_audios:
            tw = output_dir / f"_mix_tmp_{stem_name}.wav"
            torchaudio.save(str(tw), audio, model.samplerate)
            tmp_wavs.append(tw)

        # ffmpeg amix: suma normalizada de todos los stems
        inputs = []
        for tw in tmp_wavs:
            inputs += ["-i", str(tw)]

        n = len(tmp_wavs)
        amix_filter = f"amix=inputs={n}:duration=longest:normalize=0"

        if mp3:
            mix_cmd = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", amix_filter,
                "-b:a", "320k", str(out_path)
            ]
        else:
            mix_cmd = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", amix_filter,
                "-acodec", "pcm_s16le", str(out_path)
            ]

        result = subprocess.run(mix_cmd, capture_output=True, text=True)
        for tw in tmp_wavs:
            tw.unlink(missing_ok=True)

        if result.returncode != 0:
            error("ffmpeg fallo al mezclar stems:")
            lines = [l for l in result.stderr.splitlines() if l.strip()]
            print(color("\n".join(lines[-6:]), "91"))
            sys.exit(1)

        saved.append(out_path)
        success(f"Guardado (mezclado): {out_path.name}")

    else:
        # ── Guardar cada stem como archivo independiente ──
        for stem_name, audio in stem_audios:
            ext      = "mp3" if mp3 else "wav"
            out_path = output_dir / f"{base_name}{suffix}__{stem_name}.{ext}"

            if mp3:
                tmp_wav = output_dir / f"_mp3_tmp_{stem_name}.wav"
                torchaudio.save(str(tmp_wav), audio, model.samplerate)
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", str(tmp_wav), "-b:a", "320k", str(out_path)],
                        check=True, capture_output=True,
                    )
                    tmp_wav.unlink()
                except (subprocess.CalledProcessError, FileNotFoundError):
                    warn("ffmpeg no disponible para MP3, guardando WAV")
                    out_path = output_dir / f"{base_name}{suffix}__{stem_name}.wav"
                    tmp_wav.rename(out_path)
            else:
                torchaudio.save(str(out_path), audio, model.samplerate)

            saved.append(out_path)
            success(f"Guardado: {out_path.name}")

    return saved

# ─────────────────────────────────────────────────────────────
#  DEVICE
# ─────────────────────────────────────────────────────────────
def resolve_device(choice: str) -> str:
    if choice != "auto":
        return choice
    try:
        import torch
        if torch.cuda.is_available():     return "cuda"
        if torch.backends.mps.is_available(): return "mps"
    except ImportError:
        pass
    return "cpu"

# ─────────────────────────────────────────────────────────────
#  LISTAR PRESETS
# ─────────────────────────────────────────────────────────────
def list_presets():
    header("Presets disponibles")
    cats: dict[str, list] = {}
    for name, cfg in PRESETS.items():
        cats.setdefault(cfg["cat"], []).append((name, cfg))

    for cat, items in cats.items():
        print(color(f"\n  ── {cat} {'─'*(40-len(cat))}", "93"))
        for name, cfg in items:
            stems_str = " + ".join(cfg["stems"])
            print(f"  {color(name.ljust(16), '96')}  {cfg['desc']}")
            print(f"  {' '*16}  {dim('stems: ' + stems_str)}")

    print()
    print(color("  ── Stems individuales ", "93") + color("─"*18, "93"))
    print(f"  {color(', '.join(VALID_STEMS), '96')}")
    print()
    print("  Combinar manualmente con --stems:")
    print(f"  {dim('Ej: --stems vocals piano other')}")
    print()
    print("  Varias combinaciones de una vez con --combos:")
    print(f"  {dim('Ej: --combos vocals drums+bass guitar+piano all')}")
    print()

# ─────────────────────────────────────────────────────────────
#  RESOLVER COMBO STRING -> stems
# ─────────────────────────────────────────────────────────────
def resolve_combo(raw: str) -> tuple[str, list[str]]:
    """
    'vocals'       -> ('vocals', ['vocals'])
    'drums+bass'   -> ('drums+bass', ['drums', 'bass'])
    'all'          -> ('all', ['vocals','drums','bass','guitar','piano','other'])
    """
    raw = raw.strip()
    if raw in PRESETS:
        return raw, PRESETS[raw]["stems"]

    parts = [p.strip() for p in raw.split("+")]
    invalid = [p for p in parts if p not in VALID_STEMS]
    if invalid:
        error(f"Combo invalido '{raw}': stems desconocidos -> {', '.join(invalid)}")
        print(f"  Stems validos  : {', '.join(VALID_STEMS)}")
        print(f"  Presets validos: {', '.join(PRESETS.keys())}")
        sys.exit(1)

    return "+".join(parts), list(dict.fromkeys(parts))

# ─────────────────────────────────────────────────────────────
#  EPILOG DEL HELP
# ─────────────────────────────────────────────────────────────
EPILOG = """
PRESETS RAPIDOS
─────────────────────────────────────────────────────────
  vocals          Solo voz
  vocals+guitar   Voz + Guitarra
  vocals+piano    Voz + Piano
  vocals+bass     Voz + Bajo
  drums           Solo bateria
  bass            Solo bajo
  drums+bass      Bateria + Bajo (seccion ritmica)
  guitar          Solo guitarra
  piano           Solo piano
  guitar+piano    Guitarra + Piano
  band            Bateria + Bajo + Guitarra
  instrumental    Todo sin voz
  karaoke         Pista karaoke (sin voz)
  other           Elementos no clasificados
  all             Los 6 stems por separado

STEMS INDIVIDUALES disponibles:
  vocals  drums  bass  guitar  piano  other

EJEMPLOS
─────────────────────────────────────────────────────────
  # Audio: un solo preset
  python3.12 IA_audio_separator.py cancion.mp3 --preset vocals

  # Video: extrae audio automaticamente y separa
  python3.12 IA_audio_separator.py concierto.mp4 --preset vocals+guitar

  # Stems manuales (cualquier combinacion)
  python3.12 IA_audio_separator.py cancion.mp3 --stems vocals piano other

  # Multiples combos en un solo comando
  python3.12 IA_audio_separator.py cancion.mp3 --combos vocals drums+bass all
  python3.12 IA_audio_separator.py cancion.mp3 --combos vocals+guitar drums+bass+other karaoke

  # Exportar como MP3 320k (requiere ffmpeg)
  python3.12 IA_audio_separator.py cancion.mp3 --preset all --mp3

  # Carpeta de salida personalizada + GPU NVIDIA
  python3.12 IA_audio_separator.py video.mkv --preset all --output ./stems --device cuda

  # Ver todos los presets en detalle
  python3.12 IA_audio_separator.py --list-presets

NOTAS
─────────────────────────────────────────────────────────
  * Primera ejecucion: descarga el modelo Demucs ~1 GB (solo una vez)
  * Video: el audio temporal WAV se elimina automaticamente al terminar
  * Sin GPU: CPU funciona bien, solo mas lento (~5-10 min por cancion)
  * --combos acepta presets Y combinaciones libres separadas por +
    Ej: --combos vocals guitar+piano drums+bass+other all
─────────────────────────────────────────────────────────
"""

# ─────────────────────────────────────────────────────────────
#  PARSER
# ─────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="IA_audio_separator",
        description="Separador de audio/video con IA — Demucs 6-stems (vocals, drums, bass, guitar, piano, other)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )

    parser.add_argument(
        "input", nargs="?",
        help="Archivo de audio (mp3, wav, flac, ogg, m4a...) o video (mp4, mkv, mov, avi...)",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--preset", "-p",
        metavar="PRESET",
        help=(
            "Preset nombrado O combinacion libre con + entre stems.\n"
            "  Presets: vocals, drums+bass, karaoke, all, etc.\n"
            "  Libre  : drums+bass+guitar  vocals+piano+other\n"
            "  Ver todos con --list-presets"
        ),
    )
    mode.add_argument(
        "--stems", "-s",
        nargs="+", choices=VALID_STEMS, metavar="STEM",
        help=f"Stems manuales: {', '.join(VALID_STEMS)}  Ej: --stems vocals piano",
    )
    mode.add_argument(
        "--combos", "-c",
        nargs="+", metavar="COMBO",
        help=(
            "Varias combinaciones de una vez. Acepta: nombres de preset O stems unidos por +\n"
            "Ej: --combos vocals drums+bass guitar+piano all"
        ),
    )

    parser.add_argument("--output", "-o",  default="./stems_output",
                        help="Carpeta de salida (default: audioseparate_<nombre>)")
    parser.add_argument("--device", "-d",  default="auto",
                        choices=["auto", "cpu", "cuda", "mps"],
                        help="Dispositivo: auto | cpu | cuda (NVIDIA) | mps (Apple Silicon)")
    parser.add_argument("--mp3",           action="store_true",
                        help="Exportar como MP3 320k en vez de WAV (requiere ffmpeg)")
    parser.add_argument("--list-presets", "-l", action="store_true",
                        help="Mostrar todos los presets en detalle y salir")

    return parser

# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print(color("""
  ╔══════════════════════════════════════════════════╗
  ║   IA Audio Separator  |  Demucs 6-stems          ║
  ║   vocals  drums  bass  guitar  piano  other      ║
  ╚══════════════════════════════════════════════════╝
""", "96"))

    parser = build_parser()
    args   = parser.parse_args()

    if args.list_presets:
        list_presets()
        sys.exit(0)

    if not args.input:
        parser.print_help()
        print()
        error("Debes proporcionar un archivo de audio o video.")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        error(f"Archivo no encontrado: {input_path}")
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    device = resolve_device(args.device)
    info(f"Dispositivo: {color(device.upper(), '95')}")

    # ── Preparar audio: convertir si hace falta ───
    tmp_dir    = None
    audio_file = input_path
    ftype      = file_type(input_path)

    if ftype == "video" or needs_conversion(input_path):
        # Video O audio con formato no soportado por soundfile (m4a, mp3, aac, ogg...)
        tmp_dir    = Path(tempfile.mkdtemp(prefix="ia_sep_"))
        audio_file = convert_to_wav(input_path, tmp_dir)
    else:
        # WAV / FLAC: torchaudio los lee directamente sin conversion
        info(f"Formato nativo detectado ({input_path.suffix}), sin conversion necesaria")

    # Carpeta de salida: audioseparate_<slug> o la que indique --output
    if args.output == "./stems_output":
        slug = slug_from_name(input_path)
        output_dir = Path(f"audioseparate_{slug}")
    else:
        output_dir = Path(args.output)
    all_saved: list[Path] = []

    try:
        # ── Construir lista de combos ──────────────────
        combos: list[tuple[str, list[str]]] = []

        if args.combos:
            for raw in args.combos:
                label, stems = resolve_combo(raw)
                individual   = PRESETS.get(raw, {}).get("individual", False)
                combos.append((label, stems, individual))
        elif args.stems:
            stems = list(dict.fromkeys(args.stems))
            combos.append(("+".join(stems), stems, False))
        elif args.preset:
            label, stems = resolve_combo(args.preset)
            individual   = PRESETS.get(args.preset, {}).get("individual", False)
            combos.append((label, stems, individual))
        else:
            warn("Sin --preset/--stems/--combos. Usando preset 'vocals'.")
            combos.append(("vocals", PRESETS["vocals"]["stems"], False))

        # ── Plan ──────────────────────────────────────
        header(f"Plan: {len(combos)} combinacion(es) a generar")
        for i, (label, stems, individual) in enumerate(combos, 1):
            modo = "individual por stem" if individual else "archivo unico mezclado"
            print(f"  {color(str(i), '95')}. {color(label.ljust(22), '96')} {dim('-> ' + ', '.join(stems))}")
            print(f"     {dim('modo: ' + modo)}")
        print()

        # ── Ejecutar ──────────────────────────────────
        for label, stems, individual in combos:
            if individual:
                # Cada stem como archivo separado (ej: all, instrumental)
                for stem in stems:
                    saved = separate(
                        input_file = audio_file,
                        stems      = [stem],
                        output_dir = output_dir,
                        device     = device,
                        mp3        = args.mp3,
                        label      = label if len(combos) > 1 else "",
                        mix_output = False,
                    )
                    all_saved.extend(saved)
            else:
                # Un solo archivo: mezcla todos los stems pedidos
                saved = separate(
                    input_file = audio_file,
                    stems      = stems,
                    output_dir = output_dir,
                    device     = device,
                    mp3        = args.mp3,
                    label      = label if len(combos) > 1 else "",
                    mix_output = len(stems) > 1,
                )
                all_saved.extend(saved)

    finally:
        # ── Limpiar temporal ──────────────────────────
        if tmp_dir and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
            success("Audio temporal eliminado")

    # ── Resumen ───────────────────────────────────
    header(f"Completado: {len(all_saved)} archivo(s) generados")
    for f in all_saved:
        print(f"  -> {f}")
    print()
    success(f"Guardados en: {output_dir.resolve()}")
    print()


if __name__ == "__main__":
    main()
