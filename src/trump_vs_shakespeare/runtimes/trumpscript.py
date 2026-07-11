from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TrumpScriptError(ValueError):
    """Raised when the safe TrumpScript subset rejects a program."""


_ASSIGNMENT = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)\s+(?:is|are)\s+(.+?)[.!]?$", re.IGNORECASE)
_SAY = re.compile(r'^(?:say|tell)\s+"(.*)"[.!]?$', re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class TrumpProgram:
    values: dict[str, Any]
    output: tuple[str, ...]

    def get(self, name: str) -> Any:
        key = name.casefold()
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
    fact/lie booleans, say/tell output, million-scale integers, and mandatory closing
    declaration. It never executes Python source or arbitrary host commands.
    """

    def execute_file(self, path: str | Path) -> TrumpProgram:
        return self.execute(Path(path).read_text(encoding="utf-8"))

    def execute(self, source: str) -> TrumpProgram:
        meaningful = [
            line.strip()
            for line in source.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
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

            assignment = _ASSIGNMENT.match(line)
            if not assignment:
                if index == 1:
                    continue
                raise TrumpScriptError(f"Unsupported TrumpScript statement on line {index}: {line}")

            name, raw = assignment.groups()
            key = name.casefold()
            values[key] = self._value(raw.strip(), values, index)

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
        if folded in values:
            return values[folded]
        raise TrumpScriptError(f"Unknown TrumpScript value on line {line}: {raw}")
