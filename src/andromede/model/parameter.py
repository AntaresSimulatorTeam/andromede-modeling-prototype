from dataclasses import dataclass
from enum import Enum

from andromede.expression.indexing_structure import IndexingStructure


class ParameterValueType(Enum):
    FLOAT = "FLOAT"
    INTEGER = "INTEGER"
    # Needs more ?


@dataclass(frozen=True)
class Parameter:
    """
    A parameter of the model: a parameter is mainly defined by a name and expected type.
    When the model is instantiated as a component, a value must be provided for
    parameters, either as constant values or timeseries-based values.
    """

    name: str
    type: ParameterValueType
    structure: IndexingStructure


def int_parameter(
    name: str,
    structure: IndexingStructure = IndexingStructure(True, True),
) -> Parameter:
    return Parameter(name, ParameterValueType.INTEGER, structure)


def float_parameter(
    name: str,
    structure: IndexingStructure = IndexingStructure(True, True),
) -> Parameter:
    return Parameter(name, ParameterValueType.FLOAT, structure)
