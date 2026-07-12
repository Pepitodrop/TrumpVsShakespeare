from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


class ShakespeareRuntimeError(ValueError):
    """Raised when an SPL program violates the supported safe grammar."""


_POSITIVE_NOUNS = {
    "hero",
    "king",
    "kingdom",
    "rose",
    "summer",
    "heaven",
    "angel",
    "friend",
    "lord",
    "lady",
}
_NEGATIVE_NOUNS = {"coward", "villain", "devil", "pig", "toad", "worm", "curse"}
_ARTICLES = {"a", "an", "the", "my", "your", "thy", "his", "her", "its"}
_FILLER = {"as", "very"}


@dataclass(slots=True)
class Character:
    name: str
    stack: list[int] = field(default_factory=lambda: [0])

    @property
    def value(self) -> int:
        return self.stack[-1]

    def assign(self, value: int) -> None:
        self.stack[-1] = int(value)


@dataclass(frozen=True, slots=True)
class ShakespeareResult:
    values: dict[str, int]
    scenes: dict[str, dict[str, int]]
    output: tuple[int | str, ...]


class _ExpressionParser:
    def __init__(self, text: str, values: dict[str, int], listener: str):
        cleaned = re.sub(r"[^A-Za-z0-9_'-]+", " ", text).strip().casefold()
        self.tokens = cleaned.split()
        self.pos = 0
        self.values = {key.casefold(): value for key, value in values.items()}
        self.listener = listener.casefold()

    def parse(self) -> int:
        value = self._expr()
        if self.pos != len(self.tokens):
            remaining = " ".join(self.tokens[self.pos :])
            raise ShakespeareRuntimeError(f"Unparsed SPL expression tail: {remaining}")
        return value

    def _accept(self, words: Iterable[str]) -> bool:
        words = list(words)
        if self.tokens[self.pos : self.pos + len(words)] == words:
            self.pos += len(words)
            return True
        return False

    def _expect(self, word: str) -> None:
        if self.pos >= len(self.tokens) or self.tokens[self.pos] != word:
            raise ShakespeareRuntimeError(f"Expected '{word}' in SPL expression")
        self.pos += 1

    def _expr(self) -> int:
        if self._accept(["the", "sum", "of"]):
            left = self._expr()
            self._expect("and")
            return left + self._expr()
        if self._accept(["the", "difference", "between"]):
            left = self._expr()
            self._expect("and")
            return left - self._expr()
        if self._accept(["the", "product", "of"]):
            left = self._expr()
            self._expect("and")
            return left * self._expr()
        if self._accept(["the", "quotient", "between"]):
            left = self._expr()
            self._expect("and")
            right = self._expr()
            if right == 0:
                raise ShakespeareRuntimeError("SPL division by zero")
            return int(left / right)
        if self._accept(["the", "square", "of"]):
            value = self._expr()
            return value * value
        if self._accept(["the", "cube", "of"]):
            value = self._expr()
            return value * value * value
        return self._atom()

    def _atom(self) -> int:
        if self.pos >= len(self.tokens):
            raise ShakespeareRuntimeError("Expected an SPL value")
        token = self.tokens[self.pos]
        if token in {"yourself", "thyself", "thee", "thou", "you"}:
            self.pos += 1
            return self.values[self.listener]
        if token in self.values:
            self.pos += 1
            return self.values[token]
        if token.isdigit() or (token.startswith("-") and token[1:].isdigit()):
            self.pos += 1
            return int(token)

        adjectives = 0
        sign: int | None = None
        while self.pos < len(self.tokens):
            word = self.tokens[self.pos]
            self.pos += 1
            if word in _ARTICLES or word in _FILLER:
                continue
            if word in _POSITIVE_NOUNS:
                sign = 1
                break
            if word in _NEGATIVE_NOUNS:
                sign = -1
                break
            adjectives += 1
        if sign is None:
            raise ShakespeareRuntimeError("SPL constant must end in a recognized noun")
        return sign * (2**adjectives)


class ShakespeareRuntime:
    """Safe interpreter for the SPL constructs used by the game.

    Supported semantics are real SPL concepts: Dramatis Personae variables/stacks,
    Acts and Scenes, Enter/Exit/Exeunt stage management, dialogue assignments,
    arithmetic prose, Remember/Recall, and numeric/character output.
    """

    _character = re.compile(r"^([A-Za-z][A-Za-z'-]*),\s+.+\.$")
    _scene = re.compile(r"^Scene\s+[IVXLCDM]+:\s*(.+?)\.?$", re.IGNORECASE)
    _speaker = re.compile(r"^([A-Za-z][A-Za-z'-]*):$")
    _enter = re.compile(r"^\[Enter\s+(.+)\]$", re.IGNORECASE)
    _exit = re.compile(r"^\[Exit\s+(.+)\]$", re.IGNORECASE)
    _exeunt = re.compile(r"^\[Exeunt(?:\s+(.+))?\]$", re.IGNORECASE)
    _assignment = re.compile(r"^(?:You|Thou|Thee)\s+(?:are|art)(?:\s+as\s+.+?\s+as)?\s+(.+)$", re.IGNORECASE)
    _remember = re.compile(r"^Remember\s+(.+)$", re.IGNORECASE)
    _recall = re.compile(r"^Recall\b.*$", re.IGNORECASE)

    def execute_file(self, path: str | Path, initial: dict[str, int] | None = None) -> ShakespeareResult:
        return self.execute(Path(path).read_text(encoding="utf-8"), initial=initial)

    def execute(self, source: str, initial: dict[str, int] | None = None) -> ShakespeareResult:
        lines = [line.strip() for line in source.splitlines() if line.strip()]
        characters: dict[str, Character] = {}
        stage: list[str] = []
        scenes: dict[str, dict[str, int]] = {}
        output: list[int | str] = []
        current_scene: str | None = None
        speaker: str | None = None

        def snapshot() -> None:
            if current_scene:
                scenes[current_scene] = {character.name: character.value for character in characters.values()}

        for line_number, line in enumerate(lines, start=1):
            if line.startswith("#"):
                continue
            scene_match = self._scene.match(line)
            if scene_match:
                snapshot()
                current_scene = self._slug(scene_match.group(1))
                speaker = None
                continue
            if line.lower().startswith("act "):
                speaker = None
                continue
            char_match = self._character.match(line)
            if char_match and not current_scene:
                name = char_match.group(1)
                key = name.casefold()
                seed = (initial or {}).get(name, (initial or {}).get(key, 0))
                characters[key] = Character(name=name, stack=[int(seed)])
                continue
            enter = self._enter.match(line)
            if enter:
                for name in self._names(enter.group(1)):
                    key = name.casefold()
                    self._require_character(characters, key, line_number)
                    if key not in stage:
                        stage.append(key)
                speaker = None
                continue
            exit_match = self._exit.match(line)
            if exit_match:
                key = exit_match.group(1).strip().casefold()
                if key in stage:
                    stage.remove(key)
                speaker = None
                continue
            exeunt = self._exeunt.match(line)
            if exeunt:
                if exeunt.group(1):
                    for name in self._names(exeunt.group(1)):
                        key = name.casefold()
                        if key in stage:
                            stage.remove(key)
                else:
                    stage.clear()
                speaker = None
                continue
            speaker_match = self._speaker.match(line)
            if speaker_match:
                speaker = speaker_match.group(1).casefold()
                self._require_character(characters, speaker, line_number)
                if speaker not in stage:
                    raise ShakespeareRuntimeError(f"Speaker is not on stage on line {line_number}: {line}")
                continue
            if not current_scene:
                continue
            if speaker is None:
                raise ShakespeareRuntimeError(f"Dialogue has no speaker on line {line_number}: {line}")
            if len(stage) != 2:
                raise ShakespeareRuntimeError(
                    f"Exactly two characters must be on stage for dialogue (line {line_number})"
                )
            listener = stage[0] if stage[1] == speaker else stage[1]
            if speaker not in stage:
                raise ShakespeareRuntimeError(f"Speaker is not on stage on line {line_number}")
            self._execute_dialogue(line, listener, characters, output, line_number)

        snapshot()
        return ShakespeareResult(
            values={character.name: character.value for character in characters.values()},
            scenes=scenes,
            output=tuple(output),
        )

    def _execute_dialogue(
        self,
        line: str,
        listener: str,
        characters: dict[str, Character],
        output: list[int | str],
        line_number: int,
    ) -> None:
        statement = line.strip().rstrip(".!?").strip()
        assignment = self._assignment.match(statement)
        values = {key: character.value for key, character in characters.items()}
        if assignment:
            value = _ExpressionParser(assignment.group(1), values, listener).parse()
            characters[listener].assign(value)
            return
        remember = self._remember.match(statement)
        if remember:
            value = _ExpressionParser(remember.group(1), values, listener).parse()
            characters[listener].stack.append(value)
            return
        if self._recall.match(statement):
            if len(characters[listener].stack) > 1:
                characters[listener].stack.pop()
            return
        folded = statement.casefold()
        if folded in {"open your heart", "open thy heart"}:
            output.append(characters[listener].value)
            return
        if folded in {"speak your mind", "speak thy mind"}:
            output.append(chr(characters[listener].value % 0x110000))
            return
        raise ShakespeareRuntimeError(f"Unsupported SPL dialogue on line {line_number}: {line}")

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")

    @staticmethod
    def _names(value: str) -> list[str]:
        return [part.strip() for part in re.split(r"\s+and\s+|,", value, flags=re.IGNORECASE) if part.strip()]

    @staticmethod
    def _require_character(characters: dict[str, Character], key: str, line: int) -> None:
        if key not in characters:
            raise ShakespeareRuntimeError(f"Unknown Shakespeare character on line {line}: {key}")
