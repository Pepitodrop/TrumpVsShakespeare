# Contributing

## Development setup

```bash
./scripts/build_native.sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

Use Linux, WSL, or Docker because the native library targets Linux ELF.

## Rules for core-language changes

- Trump move behavior belongs in `trump_moves.tr`, not JavaScript.
- Shakespeare move behavior and stage policy belong in `.spl` programs.
- Hit, critical, random, or damage arithmetic belongs in both Assembly implementations.
- Keep x86-64 and AArch64 behavior equivalent.
- Do not add a silent high-level fallback for Assembly.
- Do not use `eval`, `exec`, or user-submitted source code.

## Pull requests

Include tests for rule changes, update the changelog when user-visible behavior changes, and verify:

```bash
ruff check src tests
pytest
docker build -t trump-vs-shakespeare:test .
```
