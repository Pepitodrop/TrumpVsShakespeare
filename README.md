# Trump vs. Shakespeare

A server-authoritative 1v1 web game in which Trump and Shakespeare choose actions in secret and resolve each round together. It is designed around three mandatory execution layers:

- **TrumpScript (`.tr`)** defines and executes Trump's complete move catalog.
- **Shakespeare Programming Language (`.spl`)** defines and executes Shakespeare's complete move catalog and runs the stage manager for initiative, energy regeneration, guard decay, and round limits.
- **Assembly (`.S`)** supplies the native pseudo-random generator, hit checks, critical-hit checks, and final damage calculation for both fighters.

Python is the safe integration runtime because the original TrumpScript implementation is Python-based. A minimal browser layer uses HTML, CSS, and JavaScript because browsers cannot run the three core languages directly. No game rule is trusted to the browser.

## Status

**Version:** `1.0.0`

The release is suitable for a single-node production deployment. Rooms are intentionally ephemeral and held in memory. Run one application replica, or add a shared room backend before horizontal scaling.

## Game modes

- **Local 1v1:** two players share one desktop or mobile device and lock one action each.
- **Online 1v1:** one player creates a six-character room code and shares the link with the opponent.
- **Mobile:** the interface is responsive and installable as a lightweight web app when served over HTTPS.

## Why every core language is essential

| Responsibility | TrumpScript | Shakespeare SPL | Assembly |
| --- | --- | --- | --- |
| Trump move names, descriptions, costs, accuracy, speed, damage, guard, healing | Required | — | — |
| Shakespeare move statistics | — | Required | — |
| Initiative comparison and round resource policy | — | Required | — |
| Random sequence, hit decision, critical decision, final damage | — | — | Required |
| Server validation and network orchestration | Python host | Python safe interpreter | Native library loaded with `ctypes` |

The server refuses to start or tests fail when any of these language components is missing or invalid. The `.tr` and `.spl` programs are data only in the sense that all real programs are data to an interpreter: they are parsed, validated, and executed at runtime, and their results directly determine game behavior.

## Safe language runtimes

The project does **not** evaluate arbitrary Python, shell commands, or user-submitted source code.

### TrumpScript

`trump_moves.tr` uses a deterministic subset derived from the original language:

- case-insensitive `is` and `are` assignments;
- `fact` and `lie` booleans;
- million-scale integer rules;
- `say` and `tell` output;
- the mandatory `America is great.` ending.

The archived upstream interpreter targets an older environment and contains platform-dependent joke restrictions. This project therefore provides a small production-safe interpreter instead of invoking the archived repository directly.

### Shakespeare Programming Language

The SPL runtime implements the constructs needed by the shipped programs:

- Dramatis Personae variables and stacks;
- Acts and Scenes;
- `Enter`, `Exit`, and `Exeunt`;
- dialogue assignments;
- prose arithmetic including sums, differences, products, quotients, squares, and cubes;
- `Remember` and `Recall` stack operations;
- numeric and character output.

`shakespeare_moves.spl` is the Bard's executable arsenal. `stage_manager.spl` is executed every round and returns the initiative delta and resource policy.

### Assembly

Native GNU Assembly implementations are included for:

- Linux x86-64 / AMD64;
- Linux AArch64 / ARM64.

The Docker build detects the target architecture and links the appropriate source into `libcombat.so`. There is deliberately no Python damage fallback; the Assembly layer is a hard runtime requirement.

## Run with Docker

```bash
git clone https://github.com/Pepitodrop/TrumpVsShakespeare.git
cd TrumpVsShakespeare
docker compose up --build
```

Open `http://localhost:8000`.

The container runs as an unprivileged user, drops Linux capabilities, uses a read-only filesystem, has a health check, and enables security headers.

## Native development

Linux or WSL is required for a non-Docker run because the native library is an ELF shared object.

```bash
./scripts/build_native.sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
uvicorn trump_vs_shakespeare.web.app:app --reload
```

Then open `http://localhost:8000`.

## Deploy online

Use the container behind a TLS-terminating reverse proxy such as Caddy, Traefik, or Nginx. WebSockets must be forwarded to `/ws/*`.

Example environment:

```env
TVS_ALLOWED_ORIGINS=https://duel.example.com
TVS_ROOM_TTL_SECONDS=7200
TVS_MAX_ROOMS=1000
TVS_ENABLE_DOCS=false
```

Production notes:

1. Keep the application at one worker and one replica because the room store is in memory.
2. Terminate HTTPS at the reverse proxy so mobile browsers can install the web app and use secure WebSockets.
3. Avoid logging WebSocket query strings because the ephemeral room token is sent during connection setup.
4. Use a shared state backend and pub/sub before running multiple replicas.

## Architecture

```text
Mobile/Desktop Browser
        │ HTTPS + WebSocket
        ▼
FastAPI room server (Python integration host)
        │
        ├── executes assets/programs/trump_moves.tr
        │      └── TrumpScript move catalog
        │
        ├── executes assets/programs/shakespeare_moves.spl
        │      └── Shakespeare move catalog
        │
        ├── executes assets/programs/stage_manager.spl each round
        │      └── initiative + resources + guard decay
        │
        └── calls native/libcombat.so
               └── Assembly RNG + hit + critical + damage
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the round protocol and trust boundaries.

## Tests and CI

```bash
./scripts/build_native.sh
pytest
```

The suite verifies that:

- TrumpScript supplies all Trump moves;
- SPL supplies all Shakespeare moves;
- SPL stage calculations affect round behavior;
- Assembly is used for randomness, hit checks, and damage;
- selected moves remain hidden until both players lock;
- local and online room creation work through the HTTP API.

GitHub Actions tests Python 3.11 and 3.12 and builds the production Docker image.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `TVS_ALLOWED_ORIGINS` | same origin | Comma-separated origins allowed for cross-origin HTTP and WebSocket access |
| `TVS_ROOM_TTL_SECONDS` | `7200` | Idle room lifetime |
| `TVS_MAX_ROOMS` | `1000` | In-memory room limit |
| `TVS_ENABLE_DOCS` | `false` | Enables `/api/docs` |
| `TVS_NATIVE_LIB` | auto-discovered | Path to `libcombat.so` |

## Satire and content note

This is fictional satire centered on public personas and literary characters. It does not claim that any dialogue or move is a real quotation, and it does not imply endorsement by Donald Trump, his organizations, William Shakespeare's estate, or the creators of the referenced programming languages.

## Attribution

- TrumpScript by Sam Shadwell, Dan Korn, Chris Brown, and Cannon Lewis: <https://github.com/samshadwell/TrumpScript> (MIT License).
- Shakespeare Programming Language was designed by Jon Åslund and Karl Wiberg. Language overview: <https://en.wikipedia.org/wiki/Shakespeare_Programming_Language>.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

MIT. See [LICENSE](LICENSE).
