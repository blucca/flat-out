"""Original Foley from oscillators and seeded noise; no samples or services.

  python make_audio.py /path/to/flat-out.wav
"""
from array import array
import math
from pathlib import Path
import random
import sys
import wave

RATE = 44100
DURATION = 16
left = array('f', [0]) * (RATE * DURATION)
right = array('f', [0]) * (RATE * DURATION)
rng = random.Random(207)


def cue(start, duration, volume, pan, sound):
    a, b = math.sqrt((1-pan)/2), math.sqrt((1+pan)/2)
    for i in range(round(duration*RATE)):
        t = i / RATE
        attack = min(1, t/.004)
        release = min(1, (duration-t)/.012)
        value = sound(t, t/duration) * volume * attack * release
        j = round(start*RATE) + i
        if 0 <= j < len(left):
            left[j] += value*a
            right[j] += value*b


def plop(start, pitch, volume, pan):
    cue(start, .16, volume, pan,
        lambda t, q: math.exp(-30*t) * (math.sin(2*math.pi*(pitch*t-170*t*t)) + .17*rng.uniform(-1, 1)))


def swish(start, duration, volume, pan, low=False):
    memory = [0.0]
    def sound(t, q):
        memory[0] = .78*memory[0] + .22*rng.uniform(-1, 1)
        noise = memory[0] if low else rng.uniform(-1, 1) - memory[0]
        tone = math.sin(2*math.pi*((105 if low else 680)*t + (95 if low else 850)*t*t))
        return math.sin(math.pi*q)**1.5 * (noise*.7 + tone*.13)
    cue(start, duration, volume, pan, sound)


plop(.70, 270, .22, -.62)
plop(1.63, 170, .31, -.62)
cue(2.15, .34, .065, -.62, lambda t, q: math.sin(2*math.pi*(330*t+340*t*t))*math.sin(math.pi*q))
swish(2.51, .75, .29, -.10)
plop(3.30, 210, .18, -.02)
# A deliberate quiet beat while the character notices the missing shadow.
swish(5.72, 1.30, .48, -.20, low=True)
swish(6.40, .34, .17, .40)
for time, pan in [(7.43,.13),(8.26,.22),(9.30,.28),(10.25,.37),(11.27,.49)]:
    plop(time, 240, .10, pan)
swish(11.78, .74, .32, .62)
cue(12.48, .21, .48, .66,
    lambda t, q: math.exp(-35*t) * (.60*rng.uniform(-1,1) + .42*math.sin(2*math.pi*(125*t-95*t*t))))
cue(12.73, .25, .055, .66,
    lambda t,q: math.sin(2*math.pi*(1120*t-550*t*t)) * math.sin(math.pi*q)**2)
plop(14.06, 580, .055, .66)

peak = max(max(abs(v) for v in left), max(abs(v) for v in right), .01)
gain = min(1, .84/peak)
pcm = array('h')
for a, b in zip(left, right):
    pcm.extend((round(a*gain*32767), round(b*gain*32767)))
if sys.byteorder != 'little':
    pcm.byteswap()
out = Path(sys.argv[1])
out.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(out), 'wb') as stream:
    stream.setnchannels(2)
    stream.setsampwidth(2)
    stream.setframerate(RATE)
    stream.writeframes(pcm.tobytes())
print(f'{out}: {DURATION}s stereo, {RATE} Hz, peak {peak*gain:.3f}')
