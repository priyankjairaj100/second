"""Metered weighted fallback for cooperative exact branches.

This is a charged-work scheduler, not a GPU/time preemption service. Both branch
callables must target the same complete canonical state. A step executes one
bounded packet, then reports its measured/declared work; this module cannot
verify that external accounting or a result's mathematical correctness.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Generic, TypeVar

T = TypeVar('T')

@dataclass(frozen=True)
class Packet(Generic[T]):
    work: int
    done: bool = False
    result: T | None = None

@dataclass(frozen=True)
class RaceResult(Generic[T]):
    result: T
    winner: str
    baseline_work: int
    repair_work: int
    cancellation_work: int
    commit_work: int

    @property
    def total_work(self) -> int:
        return self.baseline_work + self.repair_work + self.cancellation_work + self.commit_work


def _work(x: int, name: str, *, positive: bool = False) -> int:
    if type(x) is not int or x < (1 if positive else 0):
        raise ValueError(f'{name} must be an exact {"positive" if positive else "nonnegative"} integer')
    return x


def weighted_race(
    baseline_step: Callable[[], Packet[T]], repair_step: Callable[[], Packet[T]],
    *, alpha: Fraction, packet_limit: int,
    cancel: Callable[[str], int], commit: Callable[[T], int],
) -> RaceResult[T]:
    """Return the first complete result under least-served weighted scheduling.

    alpha is repair/baseline weight, and packet_limit bounds EVERY executed
    packet. Callable steps terminate and yield a terminal packet with a result.
    With standalone branch costs B,R and shares 1/(1+alpha), alpha/(1+alpha),
    branch work <= min((B+packet_limit)/w_B, (R+packet_limit)/w_R).
    Add actual cancellation and common commit work. No wall-clock bound follows.
    A reported limit violation aborts, but its already executed work cannot be
    undone; providers must satisfy the packet contract for the bound to hold.
    Exceptions abort without committing a candidate. Caller owns transactional
    disposal on exceptions; this routine only handles ordinary successful races.
    """
    if not isinstance(alpha, Fraction) or alpha <= 0:
        raise ValueError('alpha must be a positive Fraction')
    _work(packet_limit, 'packet_limit', positive=True)
    wb, wr = 1 / (1 + alpha), alpha / (1 + alpha)
    used = {'baseline': 0, 'repair': 0}
    while True:
        name = 'baseline' if used['baseline'] / wb <= used['repair'] / wr else 'repair'
        packet = (baseline_step if name == 'baseline' else repair_step)()
        if not isinstance(packet, Packet) or type(packet.done) is not bool:
            raise TypeError('branches must return a Packet with an exact boolean done flag')
        _work(packet.work, 'packet work', positive=True)
        if packet.work > packet_limit:
            raise ValueError('branch violated packet work limit')
        used[name] += packet.work
        if not packet.done:
            continue
        if packet.result is None:
            raise ValueError('terminal packet needs a non-None complete result')
        loser = 'repair' if name == 'baseline' else 'baseline'
        cleanup = _work(cancel(loser), 'cancellation work')
        final = _work(commit(packet.result), 'commit work')
        return RaceResult(packet.result, name, used['baseline'], used['repair'], cleanup, final)
