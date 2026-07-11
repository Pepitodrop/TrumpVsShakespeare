# Architecture

## Design objective

TrumpScript, Shakespeare Programming Language, and Assembly are execution dependencies rather than decorative source files. The browser is untrusted and only submits an action identifier. The server validates ownership, energy, room membership, and phase before resolving a round.

## Round protocol

1. Trump and Shakespeare each submit one hidden move.
2. The Python integration host validates the move against the catalog produced by its language runtime.
3. Native Assembly advances the deterministic per-match random state and produces initiative dice.
4. `stage_manager.spl` receives both initiative totals and calculates their difference. It also calculates energy regeneration, guard decay, and maximum energy.
5. The higher initiative acts first.
6. Native Assembly performs the accuracy comparison.
7. On a hit, native Assembly applies variance, critical-hit multiplication, guard reduction, and minimum damage.
8. The server applies health, guard, healing, and win conditions.
9. The SPL stage policy updates resources for the next round.
10. The authoritative state is broadcast to both clients over WebSockets.

## Trust boundaries

### Browser

Untrusted. It can request room creation, room joining, and actions. It cannot submit damage, health, energy, priority, or arbitrary source code.

### Python integration host

Trusted orchestration layer. It implements room ownership, hidden action locking, state transitions, validation, and networking. It hosts safe parsers for both esoteric languages and never uses `eval`, `exec`, or user-controlled subprocesses.

### TrumpScript programs

Trusted versioned application source. They control Trump's move catalog. Program loading is mandatory during engine construction.

### SPL programs

Trusted versioned application source. They control Shakespeare's move catalog and the stage policy executed every round.

### Assembly library

Trusted native code. It controls the random stream, hit decisions, critical hits, and damage. Startup fails if the shared library cannot be loaded.

## Online room model

Rooms use high-entropy player tokens and six-character human-readable room codes. The creator controls Trump; the joining player controls Shakespeare. Local rooms issue one token controlling both sides. Tokens are kept in browser `sessionStorage` and rooms expire after inactivity.

The v1.0.0 room store is process-local. This avoids pretending that a stateless multi-worker deployment is safe. Horizontal scaling requires an external state store, distributed locks, and pub/sub broadcasts.

## Failure behavior

- Invalid `.tr` or `.spl` source: engine construction fails.
- Missing Assembly library: application startup fails.
- Invalid room token: request or WebSocket connection is rejected.
- Duplicate action: rejected without changing state.
- Insufficient energy or wrong move ownership: rejected by the server.
- Room inactivity: room is removed by the cleanup task.
