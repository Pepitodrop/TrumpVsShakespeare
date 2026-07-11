from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path

from trump_vs_shakespeare.models import Move
from trump_vs_shakespeare.runtimes.shakespeare import ShakespeareRuntime
from trump_vs_shakespeare.runtimes.trumpscript import TrumpScriptRuntime


class CatalogError(RuntimeError):
    """Raised when one of the executable language catalogs is incomplete."""


TRUMP_MOVE_IDS = ("executive_order", "border_wall", "covfefe_cannon", "art_of_deal")
SHAKESPEARE_METADATA = {
    "quill_thrust": (
        "Quill Thrust",
        "A quick opening line that lands before the audience can object.",
    ),
    "tragic_monologue": (
        "Tragic Monologue",
        "A costly dramatic crescendo with devastating potential.",
    ),
    "aside_parry": (
        "Aside Parry",
        "A swift aside that raises guard before returning a cutting remark.",
    ),
    "immortal_verse": (
        "Immortal Verse",
        "A restorative couplet that wounds the foe and preserves the poet.",
    ),
}


def program_path(filename: str) -> Path:
    return Path(resources.files("trump_vs_shakespeare.assets.programs").joinpath(filename))


def load_catalog() -> dict[str, Move]:
    """Return a fresh mapping backed by the once-validated immutable move entries."""

    return {move.id: move for move in _catalog_entries()}


@lru_cache(maxsize=1)
def _catalog_entries() -> tuple[Move, ...]:
    moves: list[Move] = []
    trump = TrumpScriptRuntime().execute_file(program_path("trump_moves.tr"))
    for move_id in TRUMP_MOVE_IDS:
        move = Move(
            id=move_id,
            owner="trump",
            name=str(trump.get(f"{move_id}_name")),
            description=str(trump.get(f"{move_id}_description")),
            damage=trump.scaled_int(f"{move_id}_damage"),
            cost=trump.scaled_int(f"{move_id}_cost"),
            accuracy=trump.scaled_int(f"{move_id}_accuracy"),
            priority=trump.scaled_int(f"{move_id}_priority"),
            guard=trump.scaled_int(f"{move_id}_guard"),
            heal=trump.scaled_int(f"{move_id}_heal"),
        )
        _validate(move)
        moves.append(move)

    bard = ShakespeareRuntime().execute_file(program_path("shakespeare_moves.spl"))
    for move_id, (name, description) in SHAKESPEARE_METADATA.items():
        try:
            scene = bard.scenes[move_id]
        except KeyError as error:
            raise CatalogError(f"SPL scene is missing: {move_id}") from error
        move = Move(
            id=move_id,
            owner="shakespeare",
            name=name,
            description=description,
            damage=scene["Hamlet"],
            cost=scene["Romeo"],
            accuracy=scene["Juliet"],
            priority=scene["Ophelia"],
            guard=scene["Macbeth"],
            heal=scene["Othello"],
        )
        _validate(move)
        moves.append(move)

    if len(moves) != 8 or len({move.id for move in moves}) != 8:
        raise CatalogError("Exactly eight unique executable moves are required")
    return tuple(moves)


def _validate(move: Move) -> None:
    if not 0 <= move.damage <= 50:
        raise CatalogError(f"Invalid damage for {move.id}: {move.damage}")
    if not 0 <= move.cost <= 10:
        raise CatalogError(f"Invalid cost for {move.id}: {move.cost}")
    if not 1 <= move.accuracy <= 100:
        raise CatalogError(f"Invalid accuracy for {move.id}: {move.accuracy}")
    if not 0 <= move.priority <= 10:
        raise CatalogError(f"Invalid priority for {move.id}: {move.priority}")
    if not 0 <= move.guard <= 50 or not 0 <= move.heal <= 50:
        raise CatalogError(f"Invalid guard/heal for {move.id}")
