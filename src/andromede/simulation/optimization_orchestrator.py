from typing import Dict, List, Tuple

from andromede.model.variable import Variable
from andromede.simulation.optimization import (
    OptimizationProblem,
    OrchestrationMethod,
    build_problem,
)
from andromede.simulation.time_block import TimeBlock, TimestepComponentVariableKey
from andromede.study.data import DataBase
from andromede.study.network import Network


class OptimizationOrchestrator:
    """
    Class that handles the sequence of block optimizations, ensuring that the interblock dynamics are satisfied and implementing various resolution strategies.
    """

    def __init__(
        self,
        network: Network,
        database: DataBase,
        time_blocks: List[TimeBlock],
        orchestration_method: OrchestrationMethod,
        scenarios: int,
    ) -> None:
        self._network = network
        self._database = database
        self._time_blocks = time_blocks
        self._orchestration_method = orchestration_method
        self._scenarios = scenarios

    def run(self) -> Dict[int, Tuple[OptimizationProblem, int]]:
        initial_variables: Dict[TimestepComponentVariableKey, Variable] = {}
        output = {}
        for count, block in enumerate(self._time_blocks):
            previous_block = self._time_blocks[count - 1] if count > 0 else None
            problem = build_problem(
                self._network,
                self._database,
                block,
                self._scenarios,
                orchestration_method=self._orchestration_method,  # Interblock info...
                previous_block=previous_block,  # We use information related to another block...
                initial_variables=initial_variables,
            )
            status = problem.solver.Solve()
            # TODO : Is it possible to store only the problem object, and access the status of a solved problem with something like problem.solver.status ?
            output[block.id] = (problem, status)
            initial_variables = problem.context.get_all_component_variables()
        return output
