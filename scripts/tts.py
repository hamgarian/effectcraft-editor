"""Narration to WAV with whatever offline engine this machine has: Piper (best, needs a voice model), Windows
built-in voices, macOS `say`, or espeak-ng. Prints the duration so captions.py can spread lines over it.

  python tts.py "text" OUT.wav [--engine piper|sapi|say|espeak] [--voice NAME] [--model voice.onnx] [--rate 0]
  python tts.py @script.txt OUT.wav ...        read the text from a file
  python tts.py --list                          engines found and their voices
"""
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import wave


def engines():
    found = []
    if shutil.which("piper"):
        found.append("piper")
    if platform.system() == "Windows":
        found.append("sapi")
    if platform.system() == "Darwin" and shutil.which("say"):
        found.append("say")
    if shutil.which("espeak-ng") or shutil.which("espeak"):
        found.append("espeak")
    return found


def sapi(text, out, voice=None, rate=0):
    ps = tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8-sig")
    txt = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    txt.write(text); txt.close()
    ps.write("Add-Type -AssemblyName System.Speech\n$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
             + (f"$s.SelectVoice('{voice}')\n" if voice else "") + f"$s.Rate = {int(rate)}\n"
             f"$s.SetOutputToWaveFile('{os.path.abspath(out)}')\n$s.Speak([IO.File]::ReadAllText('{txt.name}'))\n$s.Dispose()\n")
    ps.close()
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps.name], check=True, capture_output=True)
    os.unlink(ps.name); os.unlink(txt.name)


def synth(text, out, engine=None, voice=None, model=None, rate=0):
    engine = engine or (engines() or [None])[0]
    if engine == "piper":
        if not model:
            sys.exit("piper needs --model voice.onnx (download one from the Piper voices list)")
        subprocess.run(["piper", "--model", model, "--output_file", out], input=text.encode(), check=True, capture_output=True)
    elif engine == "sapi":
        sapi(text, out, voice, rate)
    elif engine == "say":
        aiff = out + ".aiff"
        subprocess.run(["say", "-o", aiff] + (["-v", voice] if voice else []) + [text], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", aiff, out], check=True); os.unlink(aiff)
    elif engine == "espeak":
        exe = shutil.which("espeak-ng") or shutil.which("espeak")
        subprocess.run([exe, "-w", out] + (["-v", voice] if voice else []) + [text], check=True)
    else:
        sys.exit("no TTS engine found: install Piper (github.com/rhasspy/piper) or espeak-ng")
    with wave.open(out) as w:
        dur = w.getnframes() / w.getframerate()
    print(f"{out}: {dur:.2f}s ({engine})")
    return dur


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--list"]:
        print("engines:", ", ".join(engines()) or "none")
        if "sapi" in engines():
            r = subprocess.run(["powershell", "-NoProfile", "-Command", "Add-Type -AssemblyName System.Speech; "
                                "(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | % { $_.VoiceInfo.Name }"],
                               capture_output=True, text=True)
            print("sapi voices:", ", ".join(r.stdout.split("\n")).strip(", "))
        sys.exit(0)

    def opt(k, d=None):
        if k in a:
            i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
        return d
    eng, voice, model, rate = opt("--engine"), opt("--voice"), opt("--model"), opt("--rate", "0")
    if len(a) != 2:
        sys.exit(__doc__)
    text = open(a[0][1:], encoding="utf-8").read() if a[0].startswith("@") else a[0]
    synth(text, a[1], eng, voice, model, rate)
