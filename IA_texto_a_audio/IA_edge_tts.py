#!/usr/bin/env python3.12
"""
IA Edge TTS — TTS sincronizado con SRT usando Microsoft Edge TTS.
Soporta traducción offline (argostranslate) y guarda el SRT traducido.
El audio final tiene EXACTAMENTE la misma duración que el audio original.

Uso:
    python3.12 IA_edge_tts.py --translate es en --sub ./subs/audio_hd.srt --audio audio_hd.wav -o audio_hd_en.wav

Voces recomendadas:
    es-MX-DaliaNeural    es-MX-JorgeNeural
    en-US-AriaNeural     en-US-GuyNeural     en-US-JennyNeural
    en-GB-SoniaNeural    en-GB-RyanNeural
    fr-FR-DeniseNeural   de-DE-KatjaNeural   pt-BR-FranciscaNeural
    ja-JP-NanamiNeural   zh-CN-XiaoxiaoNeural

    Ver todas: edge-tts --list-voices

Requisitos:
    pip install edge-tts argostranslate
    ffmpeg y ffprobe en PATH
"""

import argparse
import asyncio
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SAMPLE_RATE = 22050

DEFAULT_VOICE_FOR_LANG = {
    "en": "en-US-AriaNeural",
    "es": "es-MX-DaliaNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ja": "ja-JP-NanamiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "it": "it-IT-ElsaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "ko": "ko-KR-SunHiNeural",
    "nl": "nl-NL-ColetteNeural",
    "pl": "pl-PL-ZofiaNeural",
    "ar": "ar-SA-ZariyahNeural",
}


# ─── ARGUMENTOS ───────────────────────────────────────────────────────────────

LANG_TABLE = """
  Código  Idioma                Voz por defecto
  ──────  ────────────────────  ─────────────────────────────
  es      Español (México)      es-MX-DaliaNeural
  en      Inglés (USA)          en-US-AriaNeural
  fr      Francés               fr-FR-DeniseNeural
  de      Alemán                de-DE-KatjaNeural
  pt      Portugués (Brasil)    pt-BR-FranciscaNeural
  it      Italiano              it-IT-ElsaNeural
  ja      Japonés               ja-JP-NanamiNeural
  zh      Chino (Mandarín)      zh-CN-XiaoxiaoNeural
  ru      Ruso                  ru-RU-SvetlanaNeural
  ko      Coreano               ko-KR-SunHiNeural
  nl      Holandés              nl-NL-ColetteNeural
  pl      Polaco                pl-PL-ZofiaNeural
  ar      Árabe                 ar-SA-ZariyahNeural

  Ver todas las voces disponibles:
    edge-tts --list-voices
    edge-tts --list-voices | grep es-MX
"""

EXAMPLES = """
ejemplos:
  ── Modo texto simple ──────────────────────────────────────────────────────
  # Texto directo (voz por defecto: es-MX-DaliaNeural)
  python3.12 IA_edge_tts.py --text "Hola, esto es una prueba de voz."

  # Texto directo con voz y salida específica
  python3.12 IA_edge_tts.py --text "Hello world" --voice en-US-AriaNeural -o salida.wav

  # Desde un archivo .txt
  python3.12 IA_edge_tts.py --txt-file mi_texto.txt --voice es-MX-JorgeNeural -o narracion.wav

  ── Modo SRT (sincronizado con video) ──────────────────────────────────────
  # Solo TTS sin traducir (voz inglés por defecto)
  python3.12 IA_edge_tts.py --sub ./subs/audio_hd.srt --audio audio_hd.wav -o audio_hd_tts.wav

  # Traducir de español a inglés + TTS sincronizado
  python3.12 IA_edge_tts.py --translate es en --sub ./subs/audio_hd.srt --audio audio_hd.wav -o audio_hd_en.wav

  # Traducir de español a francés con voz personalizada
  python3.12 IA_edge_tts.py --translate es fr --sub ./subs/audio_hd.srt --audio audio_hd.wav -o audio_hd_fr.wav --voice fr-FR-HenriNeural

  # Sin audio original (usa duración del SRT)
  python3.12 IA_edge_tts.py --translate es en --sub ./subs/audio_hd.srt -o audio_hd_en.wav

  # Guardar también los WAV individuales por segmento
  python3.12 IA_edge_tts.py --translate es en --sub ./subs/audio_hd.srt --audio audio_hd.wav -o audio_hd_en.wav --keep-segments

notas:
  - El SRT original NO se modifica. Se guarda uno nuevo: audio_hd_en.srt
  - El texto se convierte a minúsculas automáticamente antes de traducir
  - Requiere internet para Edge TTS (Microsoft). Traducción es offline.
  - Primera vez con --translate: descarga paquete de idioma ~100MB (una sola vez)
"""

def parse_args():
    p = argparse.ArgumentParser(
        prog="IA_edge_tts.py",
        description=(
            "IA Edge TTS — Genera audio TTS sincronizado desde SRT\n"
            "usando Microsoft Edge TTS con soporte de traducción offline.\n"
            + LANG_TABLE
        ),
        epilog=EXAMPLES,
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    g_req = p.add_argument_group("modo SRT (sincronizado con video)")
    g_req.add_argument(
        "--sub", default=None, metavar="ARCHIVO.srt",
        help="Archivo SRT de entrada (requerido en modo SRT)",
    )

    g_txt = p.add_argument_group("modo texto simple (sin SRT)")
    g_txt.add_argument(
        "--text", default=None, metavar="TEXTO",
        help="Texto directo a convertir en audio\n"
             "Ejemplo: --text \"Hola mundo, esto es una prueba\"",
    )
    g_txt.add_argument(
        "--txt-file", default=None, metavar="ARCHIVO.txt",
        help="Archivo .txt a convertir en audio\n"
             "Ejemplo: --txt-file mi_texto.txt",
    )

    g_opt = p.add_argument_group("argumentos opcionales")
    g_opt.add_argument(
        "--audio", default=None, metavar="ARCHIVO.wav",
        help="Audio original para medir duración total exacta\n"
             "Si no se indica, se usa el tiempo del último segmento del SRT",
    )
    g_opt.add_argument(
        "-o", "--output", default=None, metavar="SALIDA.wav",
        help="Nombre del WAV de salida\n"
             "Default: <nombre_srt>_<idioma>.wav  (ej: audio_hd_en.wav)",
    )
    g_opt.add_argument(
        "--translate", nargs=2, metavar=("FROM", "TO"), default=None,
        help="Traducir el SRT antes del TTS\n"
             "FROM y TO son códigos de la tabla de idiomas de arriba\n"
             "Ejemplo: --translate es en   (español → inglés)\n"
             "Guarda también el SRT traducido junto al original",
    )
    g_opt.add_argument(
        "--voice", default=None, metavar="NOMBRE_VOZ",
        help="Voz Edge TTS a usar\n"
             "Si no se especifica, se elige automáticamente según --translate TO\n"
             "Ejemplo: --voice en-US-GuyNeural\n"
             "Ver todas: edge-tts --list-voices",
    )
    g_opt.add_argument(
        "--max-speed", type=float, default=1.9, metavar="N",
        help="Velocidad máxima para comprimir segmentos largos (Default: 1.9)\n"
             "Rango recomendado: 1.5 – 2.0",
    )
    g_opt.add_argument(
        "--min-speed", type=float, default=0.8, metavar="N",
        help="Velocidad mínima para expandir segmentos cortos (Default: 0.8)\n"
             "Rango recomendado: 0.7 – 1.0",
    )
    g_opt.add_argument(
        "--keep-segments", action="store_true",
        help="Guardar los WAV individuales de cada segmento\n"
             "Se guardan en: <nombre_salida>_segments/",
    )
    p.add_argument("--help", "-h", action="help",
                   help="Mostrar esta ayuda y salir")
    return p.parse_args()


# ─── MENÚ ─────────────────────────────────────────────────────────────────────

def print_menu(args, voice, total_duration):
    print("\n" + "═" * 65)
    print("  IA EDGE TTS — CONFIGURACIÓN")
    print("═" * 65)
    tr = (f"{args.translate[0].upper()} → {args.translate[1].upper()} (argostranslate)"
          if args.translate else "Desactivada")
    rows = [
        ("SRT entrada",    args.sub),
        ("Audio original", args.audio or "No especificado"),
        ("Traducción",     tr),
        ("Voz Edge TTS",   voice),
        ("Duración total", f"{total_duration:.3f}s"),
        ("Vel. máx",       f"{args.max_speed}x"),
        ("Vel. mín",       f"{args.min_speed}x"),
        ("Salida WAV",     args.output),
    ]
    for label, value in rows:
        print(f"  {label:<18} : {value}")
    print("═" * 65 + "\n")


# ─── PARSEO DE SRT ────────────────────────────────────────────────────────────

def srt_to_sec(t):
    t = t.replace(",", ".")
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

def sec_to_srt(s):
    s = max(0.0, s)
    h  = int(s // 3600);  s -= h * 3600
    m  = int(s // 60);    s -= m * 60
    sc = int(s);          ms = int(round((s - sc) * 1000))
    if ms >= 1000: sc += 1; ms = 0
    return f"{h:02d}:{m:02d}:{sc:02d},{ms:03d}"

def parse_srt(srt_path):
    """Devuelve lista de dicts: {idx, start, end, text}"""
    with open(srt_path, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"(\d+)\s*\n"
        r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n"
        r"([\s\S]*?)(?=\n\s*\n\d+\s*\n|\Z)",
        re.MULTILINE,
    )
    segments = []
    for m in pattern.finditer(content):
        text = m.group(4).strip().replace("\n", " ")
        text = re.sub(r"^\[.*?\]\s*", "", text)   # quitar [SPK]
        text = re.sub(r"\s{2,}", " ", text).strip()
        text = text.lower()            # normalizar a minúsculas antes de traducir
        start = srt_to_sec(m.group(2))
        end   = srt_to_sec(m.group(3))
        if text and end > start:
            segments.append({"idx": int(m.group(1)), "start": start, "end": end, "text": text})
    return segments

def write_srt(segments, path):
    """Escribe lista de dicts como archivo SRT."""
    with open(path, "w", encoding="utf-8") as f:
        for i, s in enumerate(segments, 1):
            f.write(f"{i}\n{sec_to_srt(s['start'])} --> {sec_to_srt(s['end'])}\n{s['text']}\n\n")
    print(f"  [✓] SRT traducido guardado: {path}")


# ─── AGRUPACIÓN EN FRASES PARA TRADUCCIÓN ────────────────────────────────────

def group_into_phrases(segments):
    """
    Agrupa segmentos consecutivos en frases completas.
    Corta cuando:
      - El texto termina en puntuación final (. ! ?)
      - Hay un gap de silencio > 0.4s entre segmentos
      - El texto acumulado supera 120 caracteres
    Devuelve: lista de (indices, texto_completo, start_frase, end_frase)
    """
    groups       = []
    current_idxs = []
    current_text = ""

    for i, seg in enumerate(segments):
        current_idxs.append(i)
        current_text = (current_text + " " + seg["text"]).strip()

        ends_sentence = bool(re.search(r'[.!?]["\'\']?\s*$', seg["text"]))
        too_long      = len(current_text) > 120
        is_last       = (i == len(segments) - 1)
        gap_after     = (segments[i + 1]["start"] - seg["end"]) if i + 1 < len(segments) else 999

        if ends_sentence or too_long or is_last or gap_after > 0.4:
            start_frase = segments[current_idxs[0]]["start"]
            end_frase   = segments[current_idxs[-1]]["end"]
            groups.append((current_idxs[:], current_text, start_frase, end_frase))
            current_idxs = []
            current_text = ""

    return groups


# ─── TRADUCCIÓN OFFLINE ───────────────────────────────────────────────────────

def ensure_argos_package(from_code, to_code):
    try:
        from argostranslate import package, translate
    except ImportError:
        print("[!] Instala argostranslate: pip install argostranslate")
        sys.exit(1)

    installed = translate.get_installed_languages()
    lf = next((l for l in installed if l.code == from_code), None)
    if lf and any(t.to_lang.code == to_code for t in lf.translations_from):
        print(f"    [✓] Paquete {from_code}→{to_code} ya instalado.")
        return

    print(f"[*] Descargando paquete {from_code}→{to_code} (~100MB, solo una vez)...")
    package.update_package_index()
    available = package.get_available_packages()
    pkg = next((p for p in available if p.from_code == from_code and p.to_code == to_code), None)
    if not pkg:
        print(f"[!] No existe paquete argostranslate {from_code}→{to_code}")
        sys.exit(1)
    package.install_from_path(pkg.download())
    print(f"    [✓] Instalado.\n")

def _translate(text, from_code, to_code):
    from argostranslate import translate
    installed = translate.get_installed_languages()
    lf = next((l for l in installed if l.code == from_code), None)
    tr = next((t for t in lf.translations_from if t.to_lang.code == to_code), None)
    return tr.translate(text)

def translate_segments(segments, from_code, to_code):
    """
    Estrategia corregida — sin redistribución de palabras:

    1. Agrupa segmentos en frases completas (por puntuación / silencio / largo)
    2. Traduce cada frase COMPLETA → mejor coherencia y sin palabras inventadas
    3. Crea UN SOLO segmento por frase:
       - start = inicio del primer segmento del grupo
       - end   = fin del último segmento del grupo
       - text  = traducción completa sin partir
    4. El SRT resultante tiene menos líneas pero frases completas y correctas

    El TTS leerá cada frase de corrido respetando el rango de tiempo completo.
    """
    print(f"\n[*] Traduciendo {len(segments)} segmentos ({from_code.upper()}→{to_code.upper()})...")
    groups = group_into_phrases(segments)
    print(f"    {len(segments)} segmentos → {len(groups)} frases\n")

    result = []

    for indices, phrase_text, start_frase, end_frase in groups:
        translated = _translate(phrase_text, from_code, to_code)

        segs_label = f"[{indices[0]+1}–{indices[-1]+1}]" if len(indices) > 1 else f"[{indices[0]+1}]  "
        orig_p     = phrase_text[:45].ljust(45)
        tr_p       = translated[:45]
        print(f"  {segs_label:<9} {orig_p}  →  {tr_p}")

        result.append({
            "idx":   indices[0] + 1,
            "start": start_frase,
            "end":   end_frase,
            "text":  translated,
        })

    print(f"\n  [✓] {len(result)} frases traducidas (original: {len(segments)} segmentos).\n")
    return result


# ─── DURACIÓN DE AUDIO ────────────────────────────────────────────────────────

def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


# ─── EDGE TTS ─────────────────────────────────────────────────────────────────

async def _edge_generate(text, voice, out_mp3):
    import edge_tts
    comm = edge_tts.Communicate(text=text, voice=voice)
    await comm.save(out_mp3)

def tts_to_wav(text, voice, out_wav, tmp_dir):
    """Genera WAV desde Edge TTS. Lanza excepción si falla."""
    tmp_mp3 = os.path.join(tmp_dir, "_tmp_edge.mp3")
    asyncio.run(_edge_generate(text, voice, tmp_mp3))
    subprocess.run(
        ["ffmpeg", "-y", "-i", tmp_mp3,
         "-ar", str(SAMPLE_RATE), "-ac", "1", out_wav],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )
    if os.path.exists(tmp_mp3):
        os.remove(tmp_mp3)


# ─── FFMPEG HELPERS ───────────────────────────────────────────────────────────

def silence_wav(duration, path):
    duration = max(duration, 0.001)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono",
         "-t", f"{duration:.6f}",
         "-ar", str(SAMPLE_RATE), "-ac", "1", path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )

def speed_wav(src, dst, factor):
    """Cambia velocidad encadenando atempo (rango válido 0.5–2.0 por etapa)."""
    filters  = []
    rem = factor
    while rem > 2.0:
        filters.append("atempo=2.0"); rem /= 2.0
    while rem < 0.5:
        filters.append("atempo=0.5"); rem /= 0.5
    filters.append(f"atempo={rem:.5f}")
    subprocess.run(
        ["ffmpeg", "-y", "-i", src,
         "-af", ",".join(filters),
         "-ar", str(SAMPLE_RATE), "-ac", "1", dst],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )

def copy_wav(src, dst):
    subprocess.run(
        ["ffmpeg", "-y", "-i", src,
         "-ar", str(SAMPLE_RATE), "-ac", "1", dst],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )

def concat_wavs(paths, out):
    lst = out + ".lst"
    with open(lst, "w") as f:
        for p in paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
         "-ar", str(SAMPLE_RATE), "-ac", "1", out],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )
    os.remove(lst)

def trim_to_duration(src, dst, duration):
    """Recorta o rellena un WAV para que dure exactamente `duration` segundos."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", src,
         "-t", f"{duration:.6f}",
         "-ar", str(SAMPLE_RATE), "-ac", "1", dst],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )
    actual = get_duration(dst)
    if actual < duration - 0.01:
        # El archivo era más corto que la duración pedida → rellenar con silencio
        sil = dst + "_pad.wav"
        silence_wav(duration - actual, sil)
        tmp = dst + "_padded.wav"
        concat_wavs([dst, sil], tmp)
        os.replace(tmp, dst)
        if os.path.exists(sil): os.remove(sil)


# ─── MODO TEXTO SIMPLE ────────────────────────────────────────────────────────

def run_text_tts(args):
    """Convierte --text o --txt-file a audio WAV. No requiere SRT."""

    # ── Obtener texto ────────────────────────────────────────────────────────
    if args.text and args.txt_file:
        print("[!] Usa --text o --txt-file, no ambos a la vez.")
        sys.exit(1)

    if args.txt_file:
        txt_path = args.txt_file
        if not os.path.isfile(txt_path):
            print(f"[!] No se encontró el archivo: {txt_path}")
            sys.exit(1)
        with open(txt_path, encoding="utf-8") as f:
            text = f.read().strip()
        if not text:
            print("[!] El archivo .txt está vacío.")
            sys.exit(1)
        source_name = Path(txt_path).stem
    else:
        text = args.text.strip()
        if not text:
            print("[!] El texto está vacío.")
            sys.exit(1)
        source_name = "texto"

    # ── Determinar voz ───────────────────────────────────────────────────────
    DEFAULT_VOICE = "es-MX-DaliaNeural"
    if args.voice:
        voice = args.voice
    elif args.translate:
        lang  = args.translate[1].lower()
        voice = DEFAULT_VOICE_FOR_LANG.get(lang, DEFAULT_VOICE)
    else:
        voice = DEFAULT_VOICE

    # ── Determinar salida ────────────────────────────────────────────────────
    output_path = Path(args.output) if args.output else Path(f"{source_name}_tts.wav")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wants_wav = output_path.suffix.lower() == ".wav"
    tmp_mp3   = output_path.with_suffix("._tmp.mp3") if wants_wav else output_path

    # ── Menú ─────────────────────────────────────────────────────────────────
    print("\n" + "═" * 65)
    print("  IA EDGE TTS — MODO TEXTO SIMPLE")
    print("═" * 65)
    src_label = f"Archivo: {args.txt_file}" if args.txt_file else f"Inline ({len(text)} caracteres)"
    print(f"  Fuente             : {src_label}")
    print(f"  Voz Edge TTS       : {voice}")
    print(f"  Salida             : {output_path}")
    print("═" * 65 + "\n")

    # ── Verificar edge-tts ───────────────────────────────────────────────────
    try:
        import edge_tts
    except ImportError:
        print("[!] Instala edge-tts: pip install edge-tts")
        sys.exit(1)

    # ── Generar audio ────────────────────────────────────────────────────────
    print(f"[*] Generando audio ({len(text)} caracteres)...")

    async def _gen():
        comm = edge_tts.Communicate(text=text, voice=voice)
        await comm.save(str(tmp_mp3))

    asyncio.run(_gen())

    # ── Convertir MP3 → WAV ──────────────────────────────────────────────────
    if wants_wav:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(tmp_mp3),
             "-ar", str(SAMPLE_RATE), "-ac", "1", str(output_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        )
        if tmp_mp3.exists():
            tmp_mp3.unlink()

    duration = get_duration(str(output_path))
    print(f"\n[✓] Listo: {output_path}  ({duration:.2f}s)\n")


# ─── PROCESO PRINCIPAL ────────────────────────────────────────────────────────

def run_main():
    args = parse_args()

    # ── Modo texto simple (sin SRT) ──────────────────────────────────────────
    if args.text or args.txt_file:
        run_text_tts(args)
        return

    # ── Modo SRT: validar que --sub esté presente ────────────────────────────
    if not args.sub:
        print("[!] Debes indicar --sub ARCHIVO.srt (modo SRT) o usar --text / --txt-file (modo texto).")
        print("    Usa --help para ver todos los modos disponibles.")
        sys.exit(1)

    # Verificar edge-tts
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("[!] Instala edge-tts: pip install edge-tts")
        sys.exit(1)

    # Resolver voz
    if args.voice:
        voice = args.voice
    elif args.translate:
        voice = DEFAULT_VOICE_FOR_LANG.get(args.translate[1].lower(), "en-US-AriaNeural")
    else:
        voice = "en-US-AriaNeural"

    # Resolver ruta de salida
    srt_path = Path(args.sub)
    if args.output:
        output_wav = Path(args.output)
    else:
        suffix = f"_{args.translate[1]}" if args.translate else "_tts"
        output_wav = srt_path.parent / f"{srt_path.stem}{suffix}.wav"
    output_wav = Path(output_wav)
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    # Duración del audio original
    if args.audio:
        total_duration = get_duration(args.audio)
    else:
        total_duration = None  # se fija después de parsear SRT

    # ── 1. Parsear SRT
    print("[*] Leyendo SRT...")
    segments = parse_srt(args.sub)
    if not segments:
        print("[!] No se encontraron segmentos en el SRT.")
        sys.exit(1)
    print(f"    → {len(segments)} segmentos")

    if total_duration is None:
        total_duration = segments[-1]["end"]
        print(f"    → Duración estimada desde SRT: {total_duration:.3f}s")
    else:
        print(f"    → Duración del audio original: {total_duration:.3f}s")

    print_menu(args, voice, total_duration)

    # ── 2. Traducción (opcional) + guardar SRT traducido
    if args.translate:
        from_code = args.translate[0].lower()
        to_code   = args.translate[1].lower()
        ensure_argos_package(from_code, to_code)
        segments = translate_segments(segments, from_code, to_code)

        # Guardar SRT traducido junto al SRT original
        translated_srt = srt_path.parent / f"{srt_path.stem}_{to_code}.srt"
        write_srt(segments, str(translated_srt))

    # ── 3. Crear directorios temporales
    tmp_dir = tempfile.mkdtemp(prefix="edge_sync_")
    if args.keep_segments:
        seg_dir = str(output_wav.parent / f"{output_wav.stem}_segments")
        os.makedirs(seg_dir, exist_ok=True)
    else:
        seg_dir = tmp_dir

    try:
        print("[*] Generando y sincronizando segmentos...\n")
        pieces = []  # lista final de WAVs en orden cronológico
        stats  = {"ok": 0, "fast": 0, "slow": 0, "err": 0}

        # ── La clave del sync correcto:
        # Construimos el audio como una línea de tiempo FIJA de 0 → total_duration.
        # Cada segmento SRT ocupa exactamente su slot [start, end].
        # Los huecos entre segmentos son silencio puro.
        # No hay acumulación de errores porque siempre referenciamos
        # el tiempo absoluto del SRT, no el "cursor" relativo.

        cursor = 0.0  # posición actual en la línea de tiempo (segundos)

        for i, seg in enumerate(segments):
            start = seg["start"]
            end   = seg["end"]
            text  = seg["text"]
            slot  = end - start          # duración disponible para este segmento

            label = f"[{i+1:03d}/{len(segments)}]"
            print(f"  {label} {start:.3f}s → {end:.3f}s ({slot:.3f}s) | \"{text[:55]}{'…' if len(text)>55 else ''}\"")

            # ── Silencio EXACTO hasta el inicio de este segmento
            gap = start - cursor
            if gap > 0.005:
                sil = os.path.join(tmp_dir, f"sil_{i:04d}.wav")
                silence_wav(gap, sil)
                pieces.append(sil)
            cursor = start

            # ── Generar TTS
            raw = os.path.join(tmp_dir, f"raw_{i:04d}.wav")
            try:
                tts_to_wav(text, voice, raw, tmp_dir)
                tts_dur = get_duration(raw)
            except Exception as e:
                print(f"         ⚠ Error TTS: {e} — usando silencio")
                silence_wav(slot, raw)
                tts_dur = slot
                stats["err"] += 1

            # ── Calcular velocidad necesaria para llenar exactamente el slot
            needed = tts_dur / slot if slot > 0 else 1.0
            tag    = ""

            if needed > args.max_speed:
                tag    = f"⚡ {needed:.2f}x → clamp {args.max_speed}x"
                needed = args.max_speed
                stats["fast"] += 1
            elif needed < args.min_speed:
                tag    = f"🐢 {needed:.2f}x → clamp {args.min_speed}x"
                needed = args.min_speed
                stats["slow"] += 1

            if tag:
                print(f"         {tag}")

            # ── Ajustar velocidad
            adj = os.path.join(tmp_dir, f"adj_{i:04d}.wav")
            if abs(needed - 1.0) > 0.005:
                speed_wav(raw, adj, needed)
            else:
                copy_wav(raw, adj)

            # ── Forzar duración exacta del slot
            # (recorta si sobra, rellena con silencio si falta)
            final = os.path.join(seg_dir, f"seg_{i:04d}.wav")
            trim_to_duration(adj, final, slot)

            pieces.append(final)
            stats["ok"] += 1
            cursor = end  # avanzar cursor al final del segmento

        # ── Silencio final hasta total_duration
        tail = total_duration - cursor
        if tail > 0.005:
            sil_end = os.path.join(tmp_dir, "sil_end.wav")
            silence_wav(tail, sil_end)
            pieces.append(sil_end)
            print(f"\n  [+] Silencio final: {tail:.3f}s")

        # ── 4. Concatenar todo
        print("\n[*] Ensamblando audio final...")
        raw_concat = os.path.join(tmp_dir, "concat_raw.wav")
        concat_wavs(pieces, raw_concat)

        # ── 5. GARANTÍA FINAL: recortar/rellenar al total_duration exacto
        trim_to_duration(raw_concat, str(output_wav), total_duration)
        final_dur = get_duration(str(output_wav))

        # ── 6. Reporte
        diff = abs(final_dur - total_duration)
        print("\n" + "═" * 65)
        print("  RESULTADO")
        print("═" * 65)
        print(f"  Archivo WAV:       {output_wav}")
        if args.translate:
            print(f"  SRT traducido:     {translated_srt}")
        print(f"  Duración objetivo: {total_duration:.3f}s")
        print(f"  Duración real:     {final_dur:.3f}s")
        print(f"  Diferencia:        {diff:.4f}s  {'[✓ PERFECTO]' if diff < 0.05 else '[✓ OK]' if diff < 0.15 else '[! revisar]'}")
        print(f"  Segmentos OK:      {stats['ok']}")
        print(f"  Comprimidos:       {stats['fast']}")
        print(f"  Expandidos:        {stats['slow']}")
        if stats["err"]:
            print(f"  Errores TTS:       {stats['err']} (revisar conexión)")
        print("═" * 65)
        print(f"\n[✓] Listo: {output_wav}\n")

    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_main()
