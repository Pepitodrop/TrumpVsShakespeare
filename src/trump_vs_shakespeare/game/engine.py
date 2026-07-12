from __future__ import annotations

import time
from typing import Any

from trump_vs_shakespeare.game.catalog import load_catalog, program_path
from trump_vs_shakespeare.models import FighterState, MatchState, Move, Side
from trump_vs_shakespeare.runtimes.assembly import AssemblyCombatRuntime
from trump_vs_shakespeare.runtimes.shakespeare import ShakespeareRuntime


class GameRuleError(ValueError):
    """Raised when a player submits an action that violates match rules."""


class GameEngine:
    MAX_HEALTH = 100
    MAX_ROUNDS = 50

    def __init__(self, room_code: str, assembly: AssemblyCombatRuntime, seed: int):
        self.assembly = assembly
        self.moves = load_catalog()
        self.stage_runtime = ShakespeareRuntime()
        self.seed = seed & 0xFFFFFFFFFFFFFFFF
        self.state = MatchState(
            room_code=room_code,
            fighters={
                "trump": FighterState(side="trump"),
                "shakespeare": FighterState(side="shakespeare"),
            },
        )

    def start(self) -> None:
        if self.state.status == "waiting":
            self.state.status = "playing"
            self._log("system", "The debate begins. Choose an action in secret.")

    def submit(self, side: Side, move_id: str) -> None:
        if self.state.status != "playing":
            raise GameRuleError("The match is not accepting actions")
        if side in self.state.pending:
            raise GameRuleError("This fighter has already locked an action")
        move = self.moves.get(move_id)
        if move is None or move.owner != side:
            raise GameRuleError("That move does not belong to this fighter")
        fighter = self.state.fighters[side]
        if move.cost > fighter.energy:
            raise GameRuleError("Not enough rhetoric energy for that move")
        self.state.pending[side] = move_id
        self._log(side, f"{self._display(side)} has locked an action.", private=True)
        if len(self.state.pending) == 2:
            self._resolve_round()

    def restart(self, seed: int | None = None) -> None:
        self.seed = (seed if seed is not None else self.assembly.next_random(self.seed)) & 0xFFFFFFFFFFFFFFFF
        code = self.state.room_code
        self.state = MatchState(
            room_code=code,
            status="playing",
            fighters={
                "trump": FighterState(side="trump"),
                "shakespeare": FighterState(side="shakespeare"),
            },
        )
        self._log("system", "A new performance begins.")

    def public_state(self) -> dict[str, Any]:
        return {
            "room_code": self.state.room_code,
            "status": self.state.status,
            "round": self.state.round,
            "fighters": {side: fighter.public() for side, fighter in self.state.fighters.items()},
            "pending": {side: side in self.state.pending for side in ("trump", "shakespeare")},
            "winner": self.state.winner,
            "log": self.state.log[-16:],
            "moves": {
                side: [move.public() for move in self.moves.values() if move.owner == side]
                for side in ("trump", "shakespeare")
            },
        }

    def _resolve_round(self) -> None:
        trump_move = self.moves[self.state.pending["trump"]]
        shakespeare_move = self.moves[self.state.pending["shakespeare"]]
        trump_roll = self._roll(6)
        shakespeare_roll = self._roll(6)
        initiative = self._stage_manager(
            trump_move.priority + trump_roll,
            shakespeare_move.priority + shakespeare_roll,
        )
        delta = initiative["Chorus"]
        if delta > 0:
            order: tuple[tuple[Side, Move], ...] = (("trump", trump_move), ("shakespeare", shakespeare_move))
        elif delta < 0:
            order = (("shakespeare", shakespeare_move), ("trump", trump_move))
        else:
            order = (
                (("trump", trump_move), ("shakespeare", shakespeare_move))
                if self._roll(2) == 0
                else (("shakespeare", shakespeare_move), ("trump", trump_move))
            )

        self._log("system", f"Round {self.state.round}: {self._display(order[0][0])} has the initiative.")
        for side, move in order:
            if self.state.status == "finished":
                break
            self._execute_move(side, move)

        self.state.pending.clear()
        if self.state.status == "finished":
            return
        if self.state.round >= self.MAX_ROUNDS:
            self.state.status = "finished"
            self.state.winner = "draw"
            self._log("system", "The curtain falls after fifty rounds. The duel is a draw.")
            return

        guard_decay = initiative["Hamlet"]
        max_energy = initiative["Ophelia"]
        for side, regen_key in (("trump", "Romeo"), ("shakespeare", "Juliet")):
            fighter = self.state.fighters[side]
            fighter.energy = min(max_energy, fighter.energy + initiative[regen_key])
            fighter.guard = max(0, fighter.guard - guard_decay)
        self.state.round += 1

    def _execute_move(self, side: Side, move: Move) -> None:
        attacker = self.state.fighters[side]
        defender_side: Side = "shakespeare" if side == "trump" else "trump"
        defender = self.state.fighters[defender_side]
        if attacker.health <= 0:
            return
        attacker.energy -= move.cost
        attacker.guard = min(40, attacker.guard + move.guard)
        if move.heal:
            healed = min(move.heal, self.MAX_HEALTH - attacker.health)
            attacker.health += healed
        else:
            healed = 0

        accuracy_roll = self._roll(100)
        if move.damage and self.assembly.hit(move.accuracy, accuracy_roll):
            damage_roll = self._roll(100)
            guard_before = defender.guard
            damage = self.assembly.compute_damage(move.damage, guard_before, damage_roll, 10)
            defender.guard = max(0, defender.guard - move.damage)
            defender.health = max(0, defender.health - damage)
            critical = damage_roll < 10
            suffix = " Critical hit!" if critical else ""
            self._log(
                side,
                f"{self._display(side)} uses {move.name} for {damage} damage.{suffix}",
            )
        elif move.damage:
            self._log(side, f"{self._display(side)} uses {move.name}, but misses the mark.")
        else:
            self._log(side, f"{self._display(side)} uses {move.name}.")

        if move.guard:
            self._log(side, f"Guard rises by {move.guard}.")
        if healed:
            self._log(side, f"{self._display(side)} restores {healed} health.")
        if defender.health <= 0:
            self.state.status = "finished"
            self.state.winner = side
            self._log("system", f"{self._display(side)} wins the duel!")

    def _stage_manager(self, trump_initiative: int, shakespeare_initiative: int) -> dict[str, int]:
        result = self.stage_runtime.execute_file(
            program_path("stage_manager.spl"),
            initial={"Trump": trump_initiative, "Shakespeare": shakespeare_initiative},
        )
        required = {"Chorus", "Romeo", "Juliet", "Hamlet", "Ophelia"}
        if not required.issubset(result.values):
            raise RuntimeError("SPL stage manager did not produce every required value")
        values = result.values
        if values["Chorus"] != trump_initiative - shakespeare_initiative:
            raise RuntimeError("SPL stage manager produced an invalid initiative delta")
        if not 0 <= values["Romeo"] <= 10 or not 0 <= values["Juliet"] <= 10:
            raise RuntimeError("SPL stage manager produced invalid energy regeneration")
        if not 0 <= values["Hamlet"] <= 10:
            raise RuntimeError("SPL stage manager produced invalid guard decay")
        if not 6 <= values["Ophelia"] <= 20:
            raise RuntimeError("SPL stage manager produced an invalid maximum energy")
        return values

    def _roll(self, upper: int) -> int:
        self.seed = self.assembly.next_random(self.seed)
        return int(self.seed % upper)

    def _log(self, actor: str, message: str, private: bool = False) -> None:
        self.state.log.append(
            {
                "at": int(time.time()),
                "actor": actor,
                "message": message,
                "private": private,
            }
        )

    @staticmethod
    def _display(side: str) -> str:
        return "Trump" if side == "trump" else "Shakespeare"


def validate_runtime_stack(assembly: AssemblyCombatRuntime) -> dict[str, str]:
    """Fail startup unless every mandatory execution layer behaves as expected."""

    probe = GameEngine("PROBE0", assembly, seed=1)
    if len(probe.moves) != 8:
        raise RuntimeError("The executable move catalog is incomplete")
    stage = probe._stage_manager(7, 5)
    if stage["Chorus"] != 2:
        raise RuntimeError("The SPL stage manager failed its startup probe")
    if assembly.next_random(1) == 0:
        raise RuntimeError("The Assembly random generator failed its startup probe")
    if not assembly.hit(100, 99) or assembly.hit(0, 0):
        raise RuntimeError("The Assembly hit checker failed its startup probe")
    if assembly.compute_damage(10, 0, 50, 10) != 9:
        raise RuntimeError("The Assembly damage routine failed its startup probe")
    return {"moves": "8", "stage": "validated", "native": assembly.path.name}
