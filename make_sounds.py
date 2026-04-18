import wave
import struct
import math
import random

def save_wav(filename, samples, sample_rate=44100):
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        # Convert floats (-1.0 to 1.0) to 16-bit PCM
        buf = bytearray()
        for s in samples:
            val = int(max(-1.0, min(1.0, s)) * 32767)
            buf.extend(struct.pack('<h', val))
        f.writeframesraw(buf)

def generate_jump():
    sr = 44100
    dur = 0.2
    samples = []
    freq = 300
    for i in range(int(sr * dur)):
        t = i / sr
        freq += 15  # sweep up
        val = math.sin(2 * math.pi * freq * t)
        # Envelope shaping
        env = 1.0 - (t / dur)
        samples.append(val * env * 0.3)
    save_wav("jump.wav", samples, sr)

def generate_coin():
    sr = 44100
    dur = 0.3
    samples = []
    for i in range(int(sr * dur)):
        t = i / sr
        freq = 987.77 if t < 0.1 else 1318.51  # B5 to E6
        val = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0 # Square wave
        env = math.exp(-15 * (t if t < 0.1 else t - 0.1))
        samples.append(val * env * 0.15)
    save_wav("coin.wav", samples, sr)

def generate_shoot():
    sr = 44100
    dur = 0.15
    samples = []
    for i in range(int(sr * dur)):
        t = i / sr
        val = random.uniform(-1.0, 1.0)
        env = math.exp(-20 * t)
        samples.append(val * env * 0.4)
    save_wav("shoot.wav", samples, sr)

def generate_hit():
    sr = 44100
    dur = 0.25
    samples = []
    for i in range(int(sr * dur)):
        t = i / sr
        freq = max(40, 150 - i*0.01) # Low sweep
        val = math.sin(2 * math.pi * freq * t) + random.uniform(-0.5, 0.5)
        env = 1.0 - (t / dur)
        samples.append(val * env * 0.5)
    save_wav("hit.wav", samples, sr)

def generate_bgm():
    # Simple 4-chord 8-bit loop
    sr = 44100
    bps = 4  # notes per second
    notes = [
        # C major arpeggio
        261.63, 329.63, 392.00, 523.25,
        # F major arpeggio
        349.23, 440.00, 523.25, 698.46,
        # G major arpeggio
        392.00, 493.88, 587.33, 783.99,
        # C major arpeggio
        261.63, 329.63, 392.00, 523.25,
    ]
    samples = []
    for note in notes:
        for i in range(int(sr / bps)):
            t = i / sr
            # Square wave with slight vibrato
            vibrato = math.sin(2 * math.pi * 5 * t) * 2
            val = 1.0 if math.sin(2 * math.pi * (note + vibrato) * t) > 0 else -1.0
            # simple envelope
            env = 1.0 - (t / (1.0/bps))
            samples.append(val * env * 0.1) # low volume
    save_wav("bgm.wav", samples, sr)

print("Generating 8-bit sound effects...")
generate_jump()
generate_coin()
generate_shoot()
generate_hit()
generate_bgm()
print("Done!")
