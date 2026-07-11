from __future__ import annotations

from trump_vs_shakespeare.game.catalog import load_catalog, program_path
from trump_vs_shakespeare.runtimes.assembly import AssemblyCombatRuntime
from trump_vs_shakespeare.runtimes.shakespeare import ShakespeareRuntime
from trump_vs_shakespeare.runtimes.trumpscript import TrumpScriptRuntime


def test_trumpscript_executes_essential_catalog() -> None:
    program = TrumpScriptRuntime().execute_file(program_path("trump_moves.tr"))
    assert program.scaled_int("covfefe_cannon_damage") == 22
    assert program.get("executive_order_name") == "Executive Order"


def test_shakespeare_executes_move_scenes_and_stage_math() -> None:
    runtime = ShakespeareRuntime()
    arsenal = runtime.execute_file(program_path("shakespeare_moves.spl"))
    assert arsenal.scenes["tragic_monologue"]["Hamlet"] == 22
    assert arsenal.scenes["aside_parry"]["Macbeth"] == 12
    stage = runtime.execute_file(
        program_path("stage_manager.spl"),
        initial={"Trump": 9, "Shakespeare": 6},
    )
    assert stage.values["Chorus"] == 3
    assert stage.values["Romeo"] == 2
    assert stage.values["Ophelia"] == 10


def test_assembly_resolves_rng_hit_and_damage() -> None:
    runtime = AssemblyCombatRuntime.discover()
    assert runtime.next_random(123) != 123
    assert runtime.hit(90, 89)
    assert not runtime.hit(90, 90)
    assert runtime.compute_damage(20, 5, 50, 10) >= 13
    assert runtime.compute_damage(20, 0, 5, 10) > runtime.compute_damage(20, 0, 50, 10)


def test_catalog_requires_both_esoteric_languages() -> None:
    catalog = load_catalog()
    assert len(catalog) == 8
    assert len([move for move in catalog.values() if move.owner == "trump"]) == 4
    assert len([move for move in catalog.values() if move.owner == "shakespeare"]) == 4
