# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 1.0.x | Yes |

## Reporting a vulnerability

Please use GitHub's private security advisory feature for this repository. Do not open a public issue containing exploit details, room tokens, or deployment secrets.

Include the affected version, reproduction steps, impact, and any suggested mitigation. Acknowledgement is targeted within seven days.

## Deployment assumptions

- Use HTTPS and secure WebSockets in public deployments.
- Run one application worker and one replica for v1.0.x.
- Do not expose API documentation unless needed.
- Restrict `TVS_ALLOWED_ORIGINS` when the API and browser are deployed separately.
- Set `FORWARDED_ALLOW_IPS` only to the exact reverse-proxy IP or trusted CIDR; never use `*` on an internet-facing deployment.
- Room credentials are sent in an `Authorization` header and a WebSocket subprotocol, not in URLs. Do not configure proxies to log either credential-bearing header.
- Keep the container unprivileged and retain its read-only filesystem, `no-new-privileges`, and dropped capabilities.
- Apply infrastructure-level request-rate limits to room creation and room joining on public deployments.
- Retain the application limits for WebSocket payload size, queue depth, idle duration, message rate, send timeout, and active connections per room.
- Treat room data as ephemeral. Process restarts remove every active room and match.

## Dependency and release security

- `constraints.txt` pins the production Python dependency graph used in the image.
- The Dockerfile pins the official Python base-image digest.
- CI performs a strict `pip-audit` and publishes a CycloneDX SBOM before release.
- CI builds both AMD64 and ARM64 images and starts the AMD64 image with a read-only root filesystem.
- `/readyz` reports ready only after TrumpScript, Shakespeare SPL, and Assembly startup probes pass.
- A release tag must point to an immutable reviewed `main` commit whose CI run is fully successful.

## Language-runtime safety

The TrumpScript and SPL interpreters only load version-controlled application programs. They do not accept source code from players, call `eval` or `exec`, import requested modules, or invoke commands. Assembly symbols and argument types are explicitly bound with `ctypes`.
