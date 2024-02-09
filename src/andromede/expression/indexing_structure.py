from dataclasses import dataclass


@dataclass(frozen=True)
class IndexingStructure:
    """
    Specifies if parameters and variables should be indexed by time and/or scenarios.
    """

    time: bool
    scenario: bool

    def __or__(self, other: "IndexingStructure") -> "IndexingStructure":
        time = self.time or other.time
        scenario = self.scenario or other.scenario
        return IndexingStructure(time, scenario)
