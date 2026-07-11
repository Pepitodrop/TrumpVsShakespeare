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
- Run a single application worker for v1.0.x.
- Do not expose API documentation unless needed.
- Restrict `TVS_ALLOWED_ORIGINS` when the API and browser are deployed separately.
- Configure reverse-proxy logs to omit WebSocket query strings.
- Keep the container unprivileged and retain its read-only filesystem and dropped capabilities.

## Language-runtime safety

The TrumpScript and SPL interpreters only load version-controlled application programs. They do not accept source code from players, call `eval` or `exec`, import requested modules, or invoke commands. Assembly symbols and argument types are explicitly bound with `ctypes`.
