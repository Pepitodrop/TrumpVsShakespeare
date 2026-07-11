# v1.0.0 release contract

This document defines what the `v1.0.0` tag certifies and what it does not.

## Certified deployment model

The release is intended for one application worker in one container replica behind an HTTPS reverse proxy. The server is authoritative for room ownership, hidden actions, energy, health, guard, initiative, damage, win conditions, and rematch consent.

The release is not certified for multiple workers or replicas. Rooms are process-local. Horizontal scaling requires a shared room store, distributed locking, and pub/sub before it is safe.

## Release gates

The exact tagged commit must pass all of the following:

- Python 3.11 and Python 3.12 installation, lint, formatting, tests, and wheel builds.
- Native x86-64 Assembly execution and AArch64 Assembly validation.
- A strict `pip-audit` of the pinned production dependency graph.
- CycloneDX SBOM generation.
- AMD64 image construction from the pinned base-image digest.
- Verification of the non-root user, health check, working directory, package version, and dependency consistency.
- Startup with a read-only root filesystem and a successful `/readyz` response proving that the TrumpScript move catalog, Shakespeare move catalog, SPL stage manager, and Assembly runtime all execute correctly.
- ARM64 image construction.

## Reproducible inputs

`constraints.txt` is the production Python dependency lock for this release. The Dockerfile also pins the Python base-image digest. Changes to either require a new CI audit before a new tag.

The Debian compiler packages are used only in the discarded builder stage. The runtime image contains the pinned Python environment, application assets, and compiled native library, but no compiler toolchain.

## Required public-deployment settings

- Terminate TLS at a reverse proxy and forward WebSocket upgrades and `Sec-WebSocket-Protocol`.
- Set `FORWARDED_ALLOW_IPS` only to the exact proxy address or a trusted CIDR.
- Set `TVS_ALLOWED_ORIGINS` when the browser and API use different origins.
- Keep the container non-root, read-only, capability-free, and protected by `no-new-privileges`.
- Apply infrastructure-level rate limits to room creation and room joining. The application additionally limits WebSocket message rate, idle duration, payload size, queue depth, and active connections per room.
- Do not log `Authorization` or `Sec-WebSocket-Protocol` headers because they carry ephemeral room credentials.

## Data durability

Rooms, matches, tokens, and logs are ephemeral. Restarting the process removes all active rooms. This is intentional for v1.0.0 and must be communicated to operators and players.

## Tagging rule

The `v1.0.0` tag must point to the exact reviewed merge commit after its `main` CI run succeeds. The tag must never be moved or reused.
