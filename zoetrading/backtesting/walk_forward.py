"""Walk-forward split helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WalkForwardSplit:
    train_start: int
    train_end: int
    validation_start: int
    validation_end: int


def make_walk_forward_splits(total_length: int, *, train_size: int, validation_size: int, step: int) -> tuple[WalkForwardSplit, ...]:
    if min(total_length, train_size, validation_size, step) <= 0:
        raise ValueError("all split inputs must be positive")
    splits: list[WalkForwardSplit] = []
    start = 0
    while start + train_size + validation_size <= total_length:
        splits.append(
            WalkForwardSplit(
                train_start=start,
                train_end=start + train_size,
                validation_start=start + train_size,
                validation_end=start + train_size + validation_size,
            )
        )
        start += step
    return tuple(splits)

