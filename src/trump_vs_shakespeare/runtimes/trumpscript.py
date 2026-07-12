from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TrumpScriptError(ValueError):
    """Raised when the safe TrumpScript subset rejects a program."""


_ASSIGNMENT = re.compile(
    r"^([A-Za-z][A-Za-z0-9_]*(?:[ -][A-Za-z0-9_]+)*)\s+(?:is|are)\s+(.+?)$",
    re.IGNORECASE,
)
_SAY = re.compile(r'^(?:say|tell)\s+"(.*)"[.!]?$', re.IGNORECASE)
_SPEECH_PREFIXES = (
    "believe me,",
    "everybody knows",
    "everyone knows",
    "people are saying",
    "frankly,",
    "we all know",
    "the truth is",
)
_SPEECH_SUFFIX = re.compile(
    r",\s*(?:believe me|it(?:'|’)s tremendous|it is tremendous|very strong|okay)[.!]?$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class TrumpProgram:
    values: dict[str, Any]
    output: tuple[str, ...]

    def get(self, name: str) -> Any:
        key = _canonical_name(name)
        if key not in self.values:
            raise TrumpScriptError(f"TrumpScript variable is missing: {name}")
        return self.values[key]

    def scaled_int(self, name: str) -> int:
        value = self.get(name)
        if isinstance(value, bool):
            return int(value)
        if not isinstance(value, int):
            raise TrumpScriptError(f"{name} must be an integer or fact/lie")
        return value // 1_000_000


class TrumpScriptRuntime:
    """Deterministic, non-eval interpreter for the TrumpScript subset used by the game.

    It deliberately supports the original language's case-insensitive assignments,
    fact/lie booleans, say/tell output, million-scale integers, mandatory closing
    declaration, and tightly bounded speech-like phrasing. It never executes Python
    source or arbitrary host commands.
    """

    def execute_file(self, path: str | Path) -> TrumpProgram:
        return self.execute(Path(path).read_text(encoding="utf-8"))

    def execute(self, source: str) -> TrumpProgram:
        meaningful = [
            line.strip() for line in source.splitlines() if line.strip() and not line.lstrip().startswith("#")
        ]
        if not meaningful or meaningful[-1].rstrip(".").casefold() != "america is great":
            raise TrumpScriptError('Every program must end with "America is great."')

        values: dict[str, Any] = {}
        output: list[str] = []
        for index, line in enumerate(meaningful[:-1], start=1):
            say = _SAY.match(line)
            if say:
                output.append(say.group(1))
                continue

            assignment = _speech_assignment(line)
            if not assignment:
                if index == 1:
                    continue
                raise TrumpScriptError(f"Unsupported TrumpScript statement on line {index}: {line}")

            name, raw = assignment
            key = _canonical_name(name)
            values[key] = self._value(raw, values, index)

        return TrumpProgram(values=values, output=tuple(output))

    @staticmethod
    def _value(raw: str, values: dict[str, Any], line: int) -> Any:
        raw = raw.rstrip(".!").strip()
        folded = raw.casefold()
        if folded == "fact":
            return True
        if folded == "lie":
            return False
        if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
            return raw[1:-1]
        if re.fullmatch(r"-?\d+", raw):
            value = int(raw)
            if value <= 1_000_000:
                raise TrumpScriptError(
                    f"TrumpScript integer on line {line} must be strictly greater than one million"
                )
            return value
        reference = _canonical_name(raw)
        if reference in values:
            return values[reference]
        raise TrumpScriptError(f"Unknown TrumpScript value on line {line}: {raw}")


def _speech_assignment(line: str) -> tuple[str, str] | None:
    candidate = line.strip()
    folded = candidate.casefold()
    for prefix in _SPEECH_PREFIXES:
        if folded.startswith(prefix):
            candidate = candidate[len(prefix) :].lstrip(" ,")
            break

    candidate = _SPEECH_SUFFIX.sub("", candidate).rstrip(".!").strip()
    match = _ASSIGNMENT.match(candidate)
    if not match:
        return None
    return match.group(1), match.group(2).strip()


def _canonical_name(name: str) -> str:
    return re.sub(r"[\s-]+", "_", name.strip()).casefold()
