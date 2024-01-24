from enum import Enum


class ValueType(Enum):
    FLOAT = "FLOAT"
    INTEGER = "INTEGER"
    # Needs more ?


class ProblemContext(Enum):
    operational = 0
    investment  = 1
