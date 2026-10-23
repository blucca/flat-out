# FLAT OUT. — Flick festival edition

A wordless 16-second animated comedy. An orange outruns its shadow. Then it has
to catch up.

- **Category:** AI Animation
- **Completed:** October 22, 2026
- **Runtime:** 00:16, 960 × 540, 24 fps
- **Language:** No dialogue; English title card
- **Film:** [watermarked MP4](flick-2026.mp4)
- **Public post:** https://youtu.be/4a2o6n83Iwc
- **Original release and source:** https://blucca.github.io/flat-out/

**Submitted October 23, 2026:** [official Flick Festival entry](https://flick.art/film/flat-out-86695d).
Public creator credit: Blucca (Codex AI).

## Synopsis

A small orange ball discovers it can outrun its own shadow. The victory is
brief: the shadow overtakes it and takes a shortcut up a wall. The ball tries
to follow. At the finish, both contestants have something in common.

## Tools and creative process

Codex, an AI agent working for Blucca, created the concept, direction, Python
code, animation, editing, and original sound. Blender 4.5 LTS turns explicit
keyframes into the ball's gaze, squash, stretch, and chase. A continuous
analytic shadow crosses from floor to wall. Python oscillators and seeded
noise generate the Foley; FFmpeg assembles the final film.

Procedural animation gives the character and its shadow consistent shapes,
precise contact, and a deliberately timed visual punchline. All scene geometry
and sound are original. The source contains the scene, motion checks, timing
markers, and sound synthesis. No stock models, footage, voices, or recordings
are used.

## Festival export

This separate export uses the
[official Flick AI Film Festival watermark](https://cdn.flick.art/flickaifilmfestival-watermark.png).
The clean original remains unchanged. The watermark identifies the festival
edition; selection and awards are determined by the festival.

```sh
ffmpeg -i film.mp4 -i flickaifilmfestival-watermark.png \
  -filter_complex '[0:v]drawbox=x=12:y=ih-84:w=204:h=74:color=0x152129@0.6:t=fill[base];[1:v]scale=192:-1:flags=lanczos[mark];[base][mark]overlay=18:H-h-16:format=auto[v]' \
  -map '[v]' -map 0:a -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a copy -movflags +faststart flick-2026.mp4
```

The public post stays available through the festival's January 20, 2027
premiere. [Official rules](https://flick.art/festival/rules).
