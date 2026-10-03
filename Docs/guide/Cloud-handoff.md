# Higgsfield handoff

Prepare locally, then explicitly transfer approved assets when ready.

In GimmeStudio: **Help → Higgsfield handoff**. Tool: `sync`.

## Prepare without uploading

1. Finish local review and export a VISION package.
2. Open Cloud handoff → Prepare assistant handoff plan. This writes a local manifest of approved assets and project direction.
3. Review that plan with the assistant before using supported Higgsfield connector actions for project assembly or a final run.

## Optional API asset upload

1. Use Configure API credentials only if you have your own Higgsfield developer account. Enter the key ID and secret locally; do not paste them into a public issue or wiki.
2. Approve the assets in Asset library, then select them in Cloud handoff.
3. Choose Upload selected assets to Higgsfield. This explicitly sends those files outside the computer.
4. Successful uploads save receipts and public input URLs. Matching content hashes are skipped on repeat uploads; use the refresh option if provider-managed URLs expire.

## What is and is not synchronized

The adapter uploads media inputs. It does not create a native Cinema Studio project, synchronize a timeline or submit paid generation. Account-backed upload has not yet been verified with this installation’s user credentials. Native project synchronization remains pending. A final Higgsfield generation is a new take that needs review, not a deterministic replay of a ComfyUI graph.

## Continue learning

- [Backups and portable exports](Backups-and-export.md)
- [Assets, comparisons and review](Assets-and-review.md)

[Handbook home](Home.md)
