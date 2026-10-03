# Voices and lip-sync

Save a voice profile, record dialogue and animate a still portrait.

In GimmeStudio: **Help → Voices and lip-sync**. Tool: `voices`.

## Record dialogue

1. Open Voices & lip-sync and choose Create voice.
2. Name the profile, select a base speaker, write performance direction and keep a seed for repeatable experiments. Save changes.
3. Choose Record dialogue on the profile. Enter the spoken text and submit.
4. Watch Jobs & history until the job completes. Listen to the new audio in Assets before using it. The input script and actual duration are saved with the take.

## Animate a portrait

1. In Portrait lip-sync, choose a still image and an audio asset up to 30 seconds long.
2. Draw a rectangle around the face, covering the forehead through the chin. Avoid a rectangle containing most of the body.
3. Choose Generate lip-sync locally. Wait for its video asset, then play it at normal speed.
4. Check articulation, identity, glasses and the mouth boundary. Try a clearer, more frontal portrait if the result distorts.

## Current limits

- Qwen3-TTS profiles combine a preset speaker with performance direction; this interface does not clone voices.
- MuseTalk uses a manually selected face region on a still image. It does not track a face in moving footage.
- Stylized characters, angled faces and hands near the mouth remain experimental. A completed render needs creative review.
- The saved script is not a timed transcript. Use Dialogue & subtitles for actual audio transcription.

## Continue learning

- [Dialogue and subtitles](Dialogue-and-subtitles.md)
- [Timeline and sound](Timeline-and-sound.md)

[Handbook home](Home.md)
