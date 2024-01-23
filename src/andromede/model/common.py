from enum import Enum


class ValueType(Enum):
    FLOAT = "FLOAT"
    INTEGER = "INTEGER"
    # Needs more ?


class ProblemContext(Enum):
    simulator = 0
    xpansion_merged = 1
    xpansion_master = 2
    xpansion_subproblem = 3
