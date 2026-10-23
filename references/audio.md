# Audio: cut to the music, sound the motion

Motion edits live on the beat. Measure the music before timing anything, then check the render against it.

## Workflow
1. `python scripts/audio.py beats MUSIC --fps 20 --out beats.json`: tempo, every beat, and the hits (strong onsets: snare, impact, vocal entry), in seconds and frames. On the reference reel it read 139.7 BPM.
2. Put cuts, whips, stamps and word slams on beats or hits (`kineticType({times: beats.hits})`, captions per beat with `captions.py beats`). A reference's cut grid: `python scripts/audio.py cutsync REF.mp4 REF.mp4` lists which of its cuts sit on a beat (26 of 47 on the reference reel; the rest were flashes and glitch frames between beats - copy that, don't force every cut onto a beat).
3. Sound the motion with short effects on their frames (`audio.py sfx DIR` makes original whoosh, swish, click, impact, riser, pop): a whoosh starting 2-3 frames BEFORE a whip, an impact ON a slam, clicks per typed character, a riser into a reveal. Keep them 6-12 dB under the music.
4. `audio.py mix --cues cues.json --music MUSIC --out mix.wav`, then `audio.py mux render.mp4 mix.wav final.mp4`.
5. Check: `audio.py cutsync final.mp4 MUSIC` (cuts within 1 frame of a beat/hit) and `audio.py check REF final.mp4` (loudness, true peak, sync lag).

## Rules
- Loudness for social feeds: about -14 LUFS integrated, true peak at or under -1 dBTP; the mixer limits peaks to -1 dBFS but doesn't normalise loudness, so check it.
- Audio leads picture by a frame or two on hits (the ear forgives early sound, not late sound).
- Music you don't own never goes into an output file. For a private comparison, play the reference's own audio beside the edit (a comparison page), or use music you have rights to.
- Periodic music makes sync ambiguous (every beat matches): `check` takes the smallest shift that fits; confirm on a distinctive hit.
