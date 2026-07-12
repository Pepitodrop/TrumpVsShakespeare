# Changelog

All notable changes follow Keep a Changelog conventions. The project uses Semantic Versioning.

## [Unreleased]

### Changed

- Reworked the safe TrumpScript subset to accept bounded speech-style prefixes, suffixes, and natural multi-word identifiers while remaining deterministic and fail-closed.
- Rewrote the executable Trump move catalog as a speech-shaped program without changing any move statistics or game balance.

## [1.0.0] - 2026-07-12

### Added

- Local hot-seat and online room-based 1v1 modes.
- Responsive mobile-first battlefield and installable web-app manifest.
- Safe TrumpScript subset runtime and executable Trump move catalog.
- Safe Shakespeare Programming Language runtime with executable move scenes and round stage manager.
- Mandatory x86-64 and AArch64 Assembly combat library.
- Server-authoritative hidden action locking, energy, guard, healing, initiative, critical hits, and win conditions.
- Mutual-consent online rematches.
- Runtime startup probes covering TrumpScript, Shakespeare SPL, and native Assembly.
- Serialized and time-bounded WebSocket broadcasts, idle limits, per-connection message-rate limits, and per-room connection caps.
- Docker image, Docker Compose configuration, non-root runtime, read-only deployment profile, readiness checks, and security headers.
- Pinned production Python dependency graph and pinned Docker base-image digest.
- Python 3.11 and 3.12 tests, wheel builds, dependency integrity validation, `pip-audit`, CycloneDX SBOM generation, AMD64 runtime smoke tests, and ARM64 image builds.
- Architecture, security, contribution, deployment, release-contract, and third-party attribution documentation.

### Security

- Room credentials are excluded from URLs and sent through the HTTP `Authorization` header or negotiated WebSocket subprotocol.
- Forwarded headers are trusted only from explicitly configured proxy addresses.
- Invalid deployment limits fail application startup instead of silently falling back.
