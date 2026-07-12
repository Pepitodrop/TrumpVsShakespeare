# Changelog

All notable changes follow Keep a Changelog conventions. The project uses Semantic Versioning.

## [Unreleased]

## [1.0.1] - 2026-07-12

### Changed

- Reworked the safe TrumpScript subset to accept bounded speech-style prefixes, suffixes, and natural multi-word identifiers while remaining deterministic and fail-closed.
- Rewrote the executable Trump move catalog as a speech-shaped program without changing any move statistics or game balance.
- Start the production container through `python -m trump_vs_shakespeare.cli` instead of the generated console-script wrapper.
- Bind Docker Compose to loopback by default and document an explicit override for public reverse-proxy deployments.
- Expanded the README with a complete gameplay walkthrough, move statistics, round resolution, architecture, security model, and production deployment contract.

### Fixed

- Removed the Compose `init` wrapper that failed with `operation not permitted` on confined Docker installations.
- Added a real Docker Compose startup/readiness test to CI so the supported launch path is exercised before release.
- Close WebSockets for rooms purged during room creation and for all rooms during graceful application shutdown.
- Serve an explicit favicon and include it in the service-worker cache, eliminating the browser's `/favicon.ico` 404.
- Added the missing Ruff formatting gate promised by the release contract.
- Removed the obsolete one-shot `v1.0.0` tagging workflow after the immutable tag had been created.

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
