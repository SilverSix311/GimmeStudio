# Backups and portable exports

Protect project work and move a reviewed production between installations.

In GimmeStudio: **Help → Backups and portable exports**. Tool: `handoff`.

## Export and import a production

1. Review the project’s assets, selected takes, captions and unresolved notes.
2. Open Export & handoff → Export local VISION package. Download the ZIP or keep its saved workspace copy.
3. The package includes project records, media, workflows, shot instructions, subtitle sidecars and supported advanced files such as saved Blender scenes. Voice profiles and speech metadata travel with it.
4. To import, place the ZIP inside the workspace and choose Import a VISION package with its relative path. Import creates an independent project.
5. Check references and rebind imported workflow paths before running them. Verify important media and subtitles after import.

## Back up the whole installation

A VISION package is a production handoff, not a copy of every model or tool. For a full portable backup, finish active jobs and stop the studio, then copy the whole project folder to your chosen backup location. Preserve Studio/gimmestudio.sqlite3 together with project files; avoid copying a live database piecemeal. User contains private settings and any configured API credentials, so keep full backups private.

## Recovery

- Restore trashed items in Jobs & history.
- If the page reports a stale revision, reload before editing again; another save changed the project.
- After a reconnect, collect completed ComfyUI results from its retained history.

## Continue learning

- [Higgsfield handoff](Cloud-handoff.md)
- [Troubleshooting and known limits](Troubleshooting.md)

[Handbook home](Home.md)
