# Trump vs. Shakespeare

Play this game online at **[game.luisbenedikt.de](https://game.luisbenedikt.de/)**.

A server-authoritative, simultaneous-turn 1v1 browser game in which Trump and Shakespeare secretly choose actions and let three mandatory execution layers resolve the debate:

- **TrumpScript (`.tr`)** defines and executes Trump's complete move catalog.
- **Shakespeare Programming Language (`.spl`)** defines and executes Shakespeare's move catalog and the round stage policy.
- **Assembly (`.S`)** supplies the native pseudo-random generator, hit checks, critical-hit checks, and final damage calculation.

Python and FastAPI securely connect those runtimes, validate every action, manage rooms, and synchronize online matches. The browser only displays state and submits action identifiers; it never decides damage, health, energy, initiative, winners, or room ownership.

## Status

**Version:** `1.0.2`

The certified deployment target is **one application worker in one container replica behind an HTTPS reverse proxy**. Rooms and matches are intentionally ephemeral and stored in process memory. Horizontal scaling requires a shared room backend, distributed locking, and pub/sub first.

## Quick start

Requirements:

- Docker Engine with Docker Compose v2;
- an AMD64 or ARM64 Linux host;
- port 8000 available on loopback.

```bash
git clone https://github.com/Pepitodrop/TrumpVsShakespeare.git
cd TrumpVsShakespeare
docker compose up --build
```

Open `http://localhost:8000`.

Verify all three mandatory runtimes:

```bash
curl --fail http://127.0.0.1:8000/readyz
```

A ready server returns values equivalent to:

```json
{
  "status": "ready",
  "moves": "8",
  "stage": "validated",
  "native": "libcombat.so"
}
```

Stop the game with `Ctrl+C`, then remove the container and network with:

```bash
docker compose down --remove-orphans
```

The checked-in Compose service starts Python directly, runs as an unprivileged user, uses a read-only root filesystem, drops every Linux capability, enables `no-new-privileges`, and binds to `127.0.0.1` by default.

# How to play

## Objective

Reduce the opponent from **100 health to 0**. Both fighters begin with **6 energy** and **0 guard**. If neither fighter wins by the end of round 50, the duel is a draw.

## Choose a mode

### Local 1v1

Two players share one device. Trump selects and locks a move, then the device is passed to Shakespeare. The first selection remains hidden until the second player locks a move.

### Online 1v1

The creator receives Trump and a six-character room code. The joining player receives Shakespeare. Each player receives a separate high-entropy room token, and state updates are synchronized over WebSockets.

Only the waiting-room panel is shown until the second player joins. The invitation URL contains only the room code; player credentials are kept out of URLs.

## What the statistics mean

| Stat | Meaning |
| --- | --- |
| `DMG` | Base damage before Assembly applies random variation, critical hits, and guard |
| `EN` | Energy spent when the move executes |
| `ACC` | Percentage chance that a damaging move hits |
| `SPD` | Priority added to the initiative roll |
| `GRD` | Guard added to the attacker before damage resolves |
| `HEAL` | Health restored, capped at 100 |

A move can be selected only when its energy cost is affordable. Energy is deducted when the move executes, including when an attack misses.

## Energy management

Energy is server-authoritative and visible as a `current / maximum` meter for both fighters.

- Both fighters start with **6 / 10 energy**.
- Trump and Shakespeare each recover **2 energy after every completed round**.
- Recovery is capped at **10 energy**.
- A 2-energy move followed by 2 recovery ends at the same visible energy value; the round log records the recovered totals so this is not mistaken for a missing deduction.
- Unaffordable moves are disabled in the browser and rejected again by the server.
- A move that never executes because its fighter is knocked out first does not spend energy.

The recovery amount, maximum energy, and guard decay are calculated by `stage_manager.spl` and included in the authoritative public state.

## Trump moves

Trump's values are executed from `trump_moves.tr`.

| Move | DMG | EN | ACC | SPD | GRD | HEAL | Role |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Executive Order | 14 | 2 | 92% | 2 | 0 | 0 | Reliable general-purpose strike |
| Tremendous Wall | 5 | 2 | 100% | 5 | 14 | 0 | Fast defensive action with guaranteed chip damage |
| Covfefe Cannon | 22 | 4 | 75% | 0 | 0 | 0 | High-risk, high-damage attack |
| Art of the Deal | 9 | 3 | 95% | 3 | 0 | 10 | Accurate attack combined with healing |

## Shakespeare moves

Shakespeare's values are executed from scenes inside `shakespeare_moves.spl`.

| Move | DMG | EN | ACC | SPD | GRD | HEAL | Role |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Quill Thrust | 14 | 1 | 92% | 3 | 0 | 0 | Efficient, quick strike |
| Tragic Monologue | 22 | 3 | 78% | 0 | 0 | 0 | Costly heavy attack |
| Aside Parry | 7 | 2 | 100% | 4 | 12 | 0 | Fast defensive action |
| Immortal Verse | 10 | 3 | 90% | 2 | 0 | 10 | Damage combined with healing |

## How a round resolves

1. **Both moves lock secretly.** The public state reveals only whether each fighter has locked an action, not which action was selected.
2. **Assembly rolls initiative.** Each fighter receives a roll from 0 through 5.
3. **SPL determines who acts first.** Move priority plus the initiative roll is passed to `stage_manager.spl`. An exact tie is broken by another Assembly roll.
4. **The first move executes.** Its energy cost is deducted. Guard and healing are applied before its attack check.
5. **Assembly checks accuracy.** A random value from 0 through 99 is compared with the move's accuracy.
6. **Assembly computes damage on a hit.** Damage receives 90–110% variation. Rolls below 10 are critical hits and multiply damage by 1.5. Existing guard is subtracted, and a successful damaging hit deals at least 1 damage.
7. **The second fighter acts only if still alive.** A fast knockout prevents the defeated fighter's selected move from executing.
8. **SPL updates resources.** Each surviving fighter regains 2 energy up to a maximum of 10, and guard decays by 4.
9. **The server broadcasts the authoritative state.** The next round begins unless someone won or round 50 produced a draw.

Guard absorbs final damage and is also reduced by the incoming move's base damage. Guard itself is capped at 40.

## Winning and rematches

The first fighter to reduce the opponent to zero health wins immediately. In online mode, a rematch begins only after both players vote for it. In local mode, the single local controller can restart after the match ends.

# What each language does

| Responsibility | TrumpScript | Shakespeare SPL | Assembly |
| --- | --- | --- | --- |
| Trump move names, descriptions and statistics | Required | — | — |
| Shakespeare move statistics | — | Required | — |
| Initiative comparison and round resource policy | — | Required | — |
| Random sequence, hit decision, critical decision and final damage | — | — | Required |
| Server validation and network orchestration | Python host | Python safe interpreter | Native library loaded with `ctypes` |

The server refuses to start when a mandatory runtime is missing or invalid. The `.tr` and `.spl` programs are parsed, validated, executed at runtime, and directly determine game behavior.

## Safe TrumpScript runtime

`trump_moves.tr` uses a deterministic, speech-shaped subset inspired by the original TrumpScript language. It supports bounded speech prefixes and suffixes, natural multi-word identifiers, `fact` and `lie`, million-scale integers, `say` and `tell`, and the mandatory `America is great.` ending.

It remains deliberately fail-closed and never invokes `eval`, `exec`, shell commands, or user-submitted source.

## Safe Shakespeare Programming Language runtime

The SPL runtime implements the constructs required by the shipped programs: Dramatis Personae variables and stacks, Acts and Scenes, stage directions, dialogue assignments, prose arithmetic, stack operations, and numeric or character output.

`shakespeare_moves.spl` is the Bard's executable arsenal. `stage_manager.spl` is executed every round and returns initiative difference, energy recovery, guard decay, and maximum energy.

## Native Assembly runtime

Native GNU Assembly implementations are included for Linux x86-64 / AMD64 and Linux AArch64 / ARM64. The Docker build detects the target architecture and links the corresponding source into `libcombat.so`. There is no Python combat fallback; the Assembly library is a hard startup dependency.

# Technical architecture

```text
Mobile/Desktop Browser
        │ HTTPS + WebSocket
        ▼
FastAPI room server
        │
        ├── executes trump_moves.tr
        │      └── Trump move catalog
        ├── executes shakespeare_moves.spl
        │      └── Shakespeare move catalog
        ├── executes stage_manager.spl every round
        │      └── initiative + energy + guard policy
        └── loads native/libcombat.so
               └── Assembly RNG + hit + critical + damage
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the round protocol and trust boundaries.

## Server-authoritative security model

The browser cannot legitimately change health, damage, energy, guard, initiative, move ownership, or winner state. The server validates every submitted action.

Room credentials are generated with Python's `secrets` module, compared with constant-time comparisons, sent in the HTTP `Authorization` header, negotiated through `Sec-WebSocket-Protocol`, and excluded from room URLs.

WebSocket protections include origin validation, authentication before acceptance, payload and queue limits, idle timeout, per-connection rate limits, active socket limits, serialized time-bounded broadcasts, and cleanup of stale or shutdown connections.

# Native development

Linux or WSL is required because the native library is an ELF shared object.

```bash
./scripts/build_native.sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check src tests
ruff format --check src tests
pytest
python -m trump_vs_shakespeare.cli
```

Then open `http://localhost:8000`.

# Production deployment

Use the container behind a TLS-terminating reverse proxy such as Caddy, Traefik, or Nginx. Forward WebSocket upgrades to `/ws/*` and preserve the `Sec-WebSocket-Protocol` header.

Example `.env`:

```env
TVS_BIND_ADDRESS=127.0.0.1
TVS_ALLOWED_ORIGINS=https://duel.example.com
TVS_ROOM_TTL_SECONDS=7200
TVS_MAX_ROOMS=1000
TVS_MAX_SOCKETS_PER_ROOM=6
TVS_SOCKET_SEND_TIMEOUT_SECONDS=3
TVS_WS_IDLE_TIMEOUT_SECONDS=60
TVS_WS_MESSAGES_PER_WINDOW=40
TVS_WS_RATE_WINDOW_SECONDS=10
TVS_ENABLE_DOCS=false
FORWARDED_ALLOW_IPS=127.0.0.1
WS_MAX_SIZE=65536
WS_MAX_QUEUE=16
KEEP_ALIVE_SECONDS=5
```

Production requirements:

1. Run one worker and one replica because room state is held in memory.
2. Terminate HTTPS at the reverse proxy for secure WebSockets and installable web-app behavior.
3. Keep `TVS_BIND_ADDRESS=127.0.0.1` when the proxy runs on the same host.
4. Set `FORWARDED_ALLOW_IPS` only to the exact proxy IP or trusted CIDR.
5. Do not log `Authorization` or `Sec-WebSocket-Protocol` headers.
6. Apply infrastructure-level rate limits to room creation and joining.
7. Communicate that active rooms disappear on application restart or deployment.
8. Add shared state, distributed locking, and pub/sub before using multiple replicas.

# Tests and release gates

GitHub Actions validates Python 3.11 and 3.12, dependency integrity, lint, formatting, tests, wheel builds, executable TrumpScript and SPL catalogs, native x86-64 execution, AArch64 Assembly syntax, authenticated HTTP/WebSocket flows, dependency auditing, SBOM generation, hardened AMD64 startup, the checked-in Docker Compose path, homepage, favicon, readiness, and ARM64 image construction.

The release contract is documented in [RELEASE.md](RELEASE.md).

# Supported scope and known limits

Version 1.0.2 is production-certified only after its release gates pass, and only for modest single-node traffic with one process and ephemeral rooms. It is not certified for multiple workers or replicas, persistent matches, zero-downtime preservation of active rooms, high traffic without external rate limiting, or direct internet exposure without an HTTPS reverse proxy.

# Satire and content note

This is fictional satire centered on public personas and literary characters. It does not claim that any dialogue or move is a real quotation, and it does not imply endorsement by Donald Trump, his organizations, William Shakespeare's estate, or the creators of the referenced programming languages.

# Attribution

- TrumpScript by Sam Shadwell, Dan Korn, Chris Brown, and Cannon Lewis: <https://github.com/samshadwell/TrumpScript> (MIT License).
- Shakespeare Programming Language was designed by Jon Åslund and Karl Wiberg.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

# License

MIT. See [LICENSE](LICENSE).
