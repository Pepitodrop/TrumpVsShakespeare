from __future__ import annotations

from trump_vs_shakespeare.game.engine import GameEngine, GameRuleError
from trump_vs_shakespeare.runtimes.assembly import AssemblyCombatRuntime


def engine() -> GameEngine:
    game = GameEngine("ABC123", AssemblyCombatRuntime.discover(), seed=42)
    game.start()
    return game


def test_round_resolves_only_after_both_players_lock() -> None:
    game = engine()
    game.submit("trump", "executive_order")
    assert game.state.round == 1
    assert game.state.pending["trump"] == "executive_order"
    game.submit("shakespeare", "quill_thrust")
    assert game.state.round == 2
    assert not game.state.pending
    assert game.state.fighters["trump"].health < 100
    assert game.state.fighters["shakespeare"].health < 100


def test_move_ownership_and_energy_are_server_authoritative() -> None:
    game = engine()
    try:
        game.submit("trump", "tragic_monologue")
    except GameRuleError as error:
        assert "does not belong" in str(error)
    else:
        raise AssertionError("Expected ownership validation")


def test_public_state_hides_selected_move() -> None:
    game = engine()
    game.submit("trump", "covfefe_cannon")
    public = game.public_state()
    assert public["pending"]["trump"] is True
    assert "covfefe_cannon" not in str(public["pending"])
