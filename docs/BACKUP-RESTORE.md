# Local backup and isolated restore

The local backup covers the engineering SQLite database, continuous queue ledger, evidence bundles, model-catalog cache, and non-secret Compose/provider configuration. SQLite is captured with its online backup API so WAL state is included transactionally. The queue lease is acquired first, and backup fails while a task is actively executing. Every stored file has a SHA-256 entry in `manifest.json`; the manifest has its own checksum. The bundle records source Git head/dirty state, runtime image IDs, SQLite and ledger schema versions, and component counts.

Create a backup and verify it into a new isolated directory:

```bash
scripts/backup.sh
scripts/restore.sh ~/.zwslcore/backups/BACKUP_DIRECTORY
```

`restore.sh` never accepts a populated target and never writes to the configured live state paths. It preserves the isolated copy and writes `restore-report.json` with checksum, SQLite integrity, task/checkpoint counts, ledger counts, evidence checksums, cache readability, RPO age, and measured RTO. The default workstation targets are RPO no greater than 24 hours and RTO no greater than 60 minutes.

Backups are restricted application data. The bundle directory is mode `0700` and files are mode `0600`; keep it on access-controlled local storage and encrypt it before any off-host transfer. `.env`, provider keys, GPG private keys, and other runtime credentials are excluded and must be recovered separately through the operator's secret process. `ollama-data` is treated as reproducible model cache and is excluded.

Open WebUI's named volume may contain account, conversation, uploaded-file, and credential data. It is excluded unless explicitly requested. To include it, configure a GPG recipient key and run:

```bash
scripts/backup.sh --include-webui-volume --gpg-recipient FINGERPRINT
```

That operation briefly stops a running Open WebUI container for a consistent volume capture, streams the volume through a restricted helper container, encrypts the archive directly to GPG output, and restarts the container. The private decryption key is never included. The isolated restore preserves the encrypted volume archive; restoring it into a Docker volume is a separate operator action and must use an isolated volume first.

Run deterministic loopback fault injection without changing Docker state:

```bash
scripts/chaos.sh --output ~/.zwslcore/evidence/operations/chaos-report.json
```

This checks reset, refused, timeout, malformed JSON, transient HTTP 503, structured edit/path-gate handling, and writes a checksummed owner-only JSON report. To exercise live recovery on the local stack, invoke the Python script explicitly:

```bash
python3 scripts/chaos.py \
  --restart-provider-during-preflight \
  --restart-service provider \
  --restart-service litellm \
  --restart-service ollama \
  --check-model-unavailable \
  --output ~/.zwslcore/evidence/operations/chaos-runtime-report.json
```

The restart options interrupt local Provider preflight and in-flight inference requests, wait for health/readiness recovery, and then verify subsequent requests. These checks restart only the named containers and preserve named volumes. Disk pressure is not simulated by filling the host filesystem, and a cold model pull is not triggered because it can consume substantial network and disk resources.

Backups remain on the same workstation by default. A local backup artifact and successful isolated restore prove local capture and restore behavior; they do not establish off-host disaster recovery or a scheduled backup cadence. Keep the latest verified backup until a newer backup and restore report both pass.
