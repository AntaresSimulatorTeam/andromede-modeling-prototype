from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PortField:
    name: str


@dataclass
class PortType:
    """
    Defines a port type.

    A port is an external interface of a model, where other
    ports can be connected.
    Only compatible ports may be connected together (?)
    """

    id: str
    fields: List[PortField]  # TODO: should we rename with "pin" ?
