#!/usr/bin/env python3.12
"""
IA_noise_audio.py - Reducción de ruido y super resolution de audio con IA
Requiere: python3.12, deepfilternet, vocos, soundfile, torch, scipy, ffmpeg (sistema)
"""

import argparse
import sys
import os
import subprocess
import tempfile
import numpy as np


# ─── Argumentos ──────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Reducción de ruido y super resolution de audio con IA",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input",
        help="Archivo de audio de entrada (wav, flac, ogg, mp3, mp4...)"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Archivo de salida\n"
             "  denoise  : default input_limpio.wav\n"
             "  superres : default input_superres.wav"
    )

    # Modo
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--superres",
        action="store_true",
        help="Super resolution de audio con Vocos (mejora calidad y frecuencia de muestreo)"
    )

    # Opciones denoise (DeepFilterNet)
    dn = parser.add_argument_group("Opciones de reducción de ruido (modo default)")
    dn.add_argument(
        "--atten-lim",
        type=float,
        default=None,
        help=(
            "Límite de atenuación de ruido en dB:\n"
            "  None = máximo (elimina todo el ruido posible)\n"
            "  100  = muy agresivo\n"
            "  55   = equilibrado (recomendado)\n"
            "  20   = suave, conserva algo de ambiente\n"
            "  10   = mínimo, casi sin cambios"
        )
    )
    dn.add_argument(
        "--no-pad",
        action="store_true",
        help="No compensar el delay del STFT"
    )
    dn.add_argument(
        "--df-model",
        default=None,
        help="Ruta a modelo DeepFilterNet alternativo"
    )

    # Opciones superres (Vocos)
    sr = parser.add_argument_group("Opciones de super resolution (--superres)")
    sr.add_argument(
        "--sr-model",
        default="general",
        choices=["general", "voice"],
        help=(
            "Modelo Vocos a usar:\n"
            "  general = vocos-mel-24khz, audio general (default)\n"
            "  voice   = vocos-mel-24khz, optimizado para voz"
        )
    )
    sr.add_argument(
        "--target-sr",
        type=int,
        default=24000,
        choices=[24000, 48000],
        help=(
            "Frecuencia de muestreo de salida:\n"
            "  24000 = 24kHz, nativo de Vocos (default)\n"
            "  48000 = 48kHz, resamplea tras vocos"
        )
    )

    # Generales
    parser.add_argument(
        "--mono",
        action="store_true",
        help="Forzar conversión a mono antes de procesar"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nivel de log (default: INFO)"
    )
    return parser.parse_args()


# ─── Utilidades ──────────────────────────────────────────────────────────────

SUPPORTED_NATIVE = {".wav", ".flac", ".ogg", ".aiff", ".aif"}

def shutil_which(name):
    import shutil
    return shutil.which(name) is not None

def needs_conversion(path):
    ext = os.path.splitext(path)[1].lower()
    return ext not in SUPPORTED_NATIVE

def convert_with_ffmpeg(input_path, force_mono=False, target_sr=48000):
    if not shutil_which("ffmpeg"):
        print("ERROR: ffmpeg no está instalado.")
        print("  Arch: sudo pacman -S ffmpeg")
        sys.exit(1)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()

    cmd = ["ffmpeg", "-y", "-i", input_path,
           "-ar", str(target_sr),
           "-c:a", "pcm_s16le"]
    if force_mono:
        cmd += ["-ac", "1"]
    cmd.append(tmp.name)

    print(f"[*] Convirtiendo '{input_path}' con ffmpeg...")
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        os.unlink(tmp.name)
        print(f"ERROR: ffmpeg no pudo convertir '{input_path}'")
        sys.exit(1)

    return tmp.name

def load_audio_sf(path, target_sr=None, force_mono=False):
    import soundfile as sf
    from scipy.signal import resample
    audio_np, sr = sf.read(path)

    if force_mono and len(audio_np.shape) > 1:
        audio_np = audio_np.mean(axis=1)

    if target_sr is not None and sr != target_sr:
        if len(audio_np.shape) > 1:
            n_samples = int(audio_np.shape[0] * target_sr / sr)
            resampled = np.zeros((n_samples, audio_np.shape[1]), dtype=np.float32)
            for c in range(audio_np.shape[1]):
                resampled[:, c] = resample(audio_np[:, c], n_samples)
            audio_np = resampled
        else:
            n_samples = int(len(audio_np) * target_sr / sr)
            audio_np = resample(audio_np, n_samples)
        sr = target_sr

    return audio_np, sr

def check_import(module, pkg, install_cmd):
    try:
        __import__(module)
    except ImportError:
        print(f"ERROR: '{pkg}' no está instalado.")
        print(f"  Instala con: {install_cmd}")
        sys.exit(1)


# ─── Modo denoise ─────────────────────────────────────────────────────────────

def run_denoise(args, return_audio=False):
    check_import("df", "deepfilternet", "python3.12 -m pip install deepfilternet")
    check_import("torch", "torch",
                 "python3.12 -m pip install torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu")
    check_import("soundfile", "soundfile", "python3.12 -m pip install soundfile")

    import torch
    import soundfile as sf
    from df.enhance import enhance, init_df

    output = args.output or f"{os.path.splitext(args.input)[0]}_limpio.wav"

    print(f"[*] Modo      : reducción de ruido (DeepFilterNet3)")
    print(f"[*] Entrada   : {args.input}")
    if not return_audio:
        print(f"[*] Salida    : {output}")
    print(f"[*] Atten lim : {args.atten_lim} dB")

    print("[*] Cargando modelo DeepFilterNet3...")
    model, df_state, _ = init_df(args.df_model) if args.df_model else init_df()

    tmp_file = None
    input_path = args.input
    if needs_conversion(args.input):
        tmp_file = convert_with_ffmpeg(args.input, force_mono=args.mono)
        input_path = tmp_file

    print("[*] Cargando audio...")
    audio_np, sr = load_audio_sf(input_path, target_sr=df_state.sr(), force_mono=args.mono)

    if len(audio_np.shape) > 1:
        channels = audio_np.shape[1]
        print(f"[*] Audio stereo ({channels} canales), procesando por canal...")
        tensors = []
        for c in range(channels):
            ch = torch.from_numpy(audio_np[:, c].astype(np.float32)).unsqueeze(0)
            enhanced_ch = enhance(model, df_state, ch,
                                  pad=not args.no_pad,
                                  atten_lim_db=args.atten_lim)
            tensors.append(enhanced_ch.squeeze().numpy())
        result = np.stack(tensors, axis=1)
    else:
        print("[*] Procesando...")
        audio_tensor = torch.from_numpy(audio_np.astype(np.float32)).unsqueeze(0)
        enhanced = enhance(model, df_state, audio_tensor,
                           pad=not args.no_pad,
                           atten_lim_db=args.atten_lim)
        result = enhanced.squeeze().numpy()

    if tmp_file and os.path.exists(tmp_file):
        os.unlink(tmp_file)

    if return_audio:
        # Devolver array en memoria para pipeline
        return result, df_state.sr()

    sf.write(output, result, df_state.sr())
    print(f"[✓] Listo: {output}")


# ─── Modo superres ────────────────────────────────────────────────────────────

SR_MODELS = {
    "general": "charactr/vocos-mel-24khz",
    "voice":   "charactr/vocos-mel-24khz",
}

def run_superres(args, audio_np=None, sr=None):
    check_import("vocos", "vocos", "python3.12 -m pip install vocos")
    check_import("torch", "torch",
                 "python3.12 -m pip install torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu")
    check_import("soundfile", "soundfile", "python3.12 -m pip install soundfile")

    import torch
    import soundfile as sf
    from vocos import Vocos
    from scipy.signal import resample as scipy_resample

    model_id = SR_MODELS[args.sr_model]
    output = args.output or f"{os.path.splitext(args.input)[0]}_superres.wav"

    print(f"[*] Modo      : super resolution (Vocos)")
    print(f"[*] Modelo    : {model_id}")
    print(f"[*] Entrada   : {args.input}")
    print(f"[*] Salida    : {output}")
    print(f"[*] Target SR : {args.target_sr} Hz")

    print("[*] Cargando modelo Vocos...")
    vocos = Vocos.from_pretrained(model_id)

    tmp_file = None
    # Si no viene audio en memoria, cargarlo desde disco
    if audio_np is None:
        input_path = args.input
        if needs_conversion(args.input):
            tmp_file = convert_with_ffmpeg(args.input, force_mono=args.mono, target_sr=24000)
            input_path = tmp_file

        print("[*] Cargando audio...")
        audio_np, sr = sf.read(input_path)

    if args.mono and len(audio_np.shape) > 1:
        audio_np = audio_np.mean(axis=1)

    is_stereo = len(audio_np.shape) > 1 and audio_np.shape[1] >= 2

    def vocos_mono(channel_np, sr_in):
        """Procesa un canal mono con Vocos. Devuelve numpy 1D a 24kHz."""
        if sr_in != 24000:
            n = int(len(channel_np) * 24000 / sr_in)
            channel_np = scipy_resample(channel_np, n)
        wav = torch.from_numpy(channel_np.astype(np.float32)).unsqueeze(0)
        with torch.no_grad():
            mel = vocos.feature_extractor(wav)
            wav_out = vocos.decode(mel)
        return wav_out.squeeze().numpy()

    def match_rms(reference, target):
        """Ajusta el nivel RMS de target para que coincida con reference."""
        rms_ref = np.sqrt(np.mean(reference ** 2))
        rms_tgt = np.sqrt(np.mean(target ** 2))
        if rms_tgt < 1e-9:
            return target
        return target * (rms_ref / rms_tgt)

    if is_stereo:
        print(f"[*] Audio estéreo — procesando L y R por separado con Vocos...")
        left_in  = audio_np[:, 0].astype(np.float32)
        right_in = audio_np[:, 1].astype(np.float32)

        left_out  = vocos_mono(left_in,  sr)
        right_out = vocos_mono(right_in, sr)

        # Igualar longitud (Vocos puede producir arrays de distinto tamaño por redondeo)
        min_len = min(len(left_out), len(right_out))
        left_out  = left_out[:min_len]
        right_out = right_out[:min_len]

        # Nivelar RMS de R respecto a L para evitar desbalance
        right_out = match_rms(left_out, right_out)

        result = np.stack([left_out, right_out], axis=1)
        print(f"[*] Procesando con Vocos... ({min_len} samples a 24kHz, estéreo)")
    else:
        channel = audio_np if len(audio_np.shape) == 1 else audio_np[:, 0]
        print(f"[*] Procesando con Vocos... ({len(channel)} samples, mono)")
        result = vocos_mono(channel.astype(np.float32), sr)

    out_sr = 24000

    # Resamplear a 48kHz si se pidió
    if args.target_sr == 48000:
        print("[*] Resampleando salida a 48000Hz...")
        if len(result.shape) > 1:
            n = int(result.shape[0] * 48000 / 24000)
            resampled = np.zeros((n, result.shape[1]), dtype=np.float32)
            for c in range(result.shape[1]):
                resampled[:, c] = scipy_resample(result[:, c], n)
            result = resampled
        else:
            n = int(len(result) * 48000 / 24000)
            result = scipy_resample(result, n)
        out_sr = 48000

    sf.write(output, result, out_sr)

    if tmp_file and os.path.exists(tmp_file):
        os.unlink(tmp_file)

    canales = "estéreo" if (len(result.shape) > 1 and result.shape[1] == 2) else "mono"
    print(f"[✓] Listo: {output} ({out_sr}Hz, {canales})")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    import logging
    logging.basicConfig(level=getattr(logging, args.log_level))
    # Silenciar logs ruidosos de librerías externas (httpx, HuggingFace)
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    logging.getLogger("huggingface_hub.utils._http").setLevel(logging.ERROR)

    if args.superres and args.atten_lim is not None:
        # Pipeline automático: denoise → superres
        print("[*] --atten-lim detectado con --superres: ejecutando denoise → superres\n")
        print("[PASO 1/2] Reducción de ruido...")
        audio_denoised, sr_denoised = run_denoise(args, return_audio=True)
        print("\n[PASO 2/2] Super resolution...")
        run_superres(args, audio_np=audio_denoised, sr=sr_denoised)
    elif args.superres:
        run_superres(args)
    else:
        run_denoise(args)


if __name__ == "__main__":
    main()
