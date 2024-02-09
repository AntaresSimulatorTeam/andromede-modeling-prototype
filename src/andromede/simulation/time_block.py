from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class TimeBlock:
    """
    One block for otimization (week in current tool).

    timesteps: list of the different timesteps of the block (0, 1, ... 168 for each hour in one week)
    """

    id: int
    timesteps: List[int]
