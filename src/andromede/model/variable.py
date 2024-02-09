from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from andromede.expression import ExpressionNode
from andromede.expression.degree import is_constant
from andromede.expression.indexing_structure import IndexingStructure


class VariableValueType(Enum):
    FLOAT = "FLOAT"
    INTEGER = "INTEGER"
    # Needs more ?


@dataclass
class Variable:
    """
    A decision variable of the model.
    """

    name: str
    data_type: VariableValueType
    lower_bound: Optional[ExpressionNode]
    upper_bound: Optional[ExpressionNode]
    structure: IndexingStructure = field(default=IndexingStructure(True, True))

    def __post_init__(self) -> None:
        if self.lower_bound and not is_constant(self.lower_bound):
            raise ValueError("Lower bounds of variables must be constant")
        if self.upper_bound and not is_constant(self.upper_bound):
            raise ValueError("Lower bounds of variables must be constant")


def int_variable(
    name: str,
    lower_bound: Optional[ExpressionNode] = None,
    upper_bound: Optional[ExpressionNode] = None,
    structural_type: Optional[IndexingStructure] = None,
) -> Variable:
    # Dirty if/else just for MyPy
    if structural_type is None:
        return Variable(name, VariableValueType.INTEGER, lower_bound, upper_bound)
    else:
        return Variable(
            name, VariableValueType.INTEGER, lower_bound, upper_bound, structural_type
        )


def float_variable(
    name: str,
    lower_bound: Optional[ExpressionNode] = None,
    upper_bound: Optional[ExpressionNode] = None,
    structure: Optional[IndexingStructure] = None,
) -> Variable:
    # Dirty if/else just for MyPy
    if structure is None:
        return Variable(name, VariableValueType.FLOAT, lower_bound, upper_bound)
    else:
        return Variable(
            name, VariableValueType.FLOAT, lower_bound, upper_bound, structure
        )
