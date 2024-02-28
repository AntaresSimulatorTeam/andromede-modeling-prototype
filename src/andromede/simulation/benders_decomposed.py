# Copyright (c) 2024, RTE (https://www.rte-france.com)
#
# See AUTHORS.txt
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0
#
# This file is part of the Antares project.

"""
The xpansion module extends the optimization module
with Benders solver related functions
"""

import pathlib
from typing import Any, Dict, List, Optional

from anytree import Node as TreeNode

from andromede.model.model import Model
from andromede.simulation.decision_tree import ConfiguredTree, create_master_network
from andromede.simulation.optimization import (
    BlockBorderManagement,
    OptimizationProblem,
    build_problem,
)
from andromede.simulation.output_values import (
    BendersDecomposedSolution,
    BendersMergedSolution,
    BendersSolution,
)
from andromede.simulation.runner import BendersRunner, MergeMPSRunner
from andromede.simulation.strategy import (
    InvestmentProblemStrategy,
    OperationalProblemStrategy,
)
from andromede.simulation.time_block import ConfiguredTree, TimeBlock
from andromede.study.data import DataBase
from andromede.study.network import Network
from andromede.utils import read_json, serialize, serialize_json


class BendersDecomposedProblem:
    """
    A simpler interface for the Benders Decomposed problem
    """

    master: OptimizationProblem
    subproblems: List[OptimizationProblem]

    emplacement: pathlib.Path
    output_path: pathlib.Path

    solution: Optional[BendersSolution]
    is_merged: bool

    def __init__(
        self,
        master: OptimizationProblem,
        subproblems: List[OptimizationProblem],
        emplacement: str = "outputs/lp",
        output_path: str = "expansion",
    ) -> None:
        self.master = master
        self.subproblems = subproblems

        self.emplacement = pathlib.Path(emplacement)
        self.output_path = pathlib.Path(output_path)

        self.solution = None
        self.is_merged = False

    def export_structure(self) -> str:
        """
        Write the structure.txt file
        """

        if not self.subproblems:
            # TODO For now, only one master and one subproblem
            raise RuntimeError("Subproblem list must have at least one sub problem")

        # A mapping similar to the Xpansion mapping for keeping track of variable indexes
        # in Master and Sub-problem files
        problem_to_candidates: Dict[str, Dict[str, int]] = {}
        candidates = set()

        problem_to_candidates["master"] = {}
        for solver_var_info in self.master.context._solver_variables.values():
            if solver_var_info.is_in_objective:
                problem_to_candidates["master"][
                    solver_var_info.name
                ] = solver_var_info.column_id
                candidates.add(solver_var_info.name)

        for problem in self.subproblems:
            problem_to_candidates[problem.name] = {}

            for solver_var_info in problem.context._solver_variables.values():
                if solver_var_info.name in candidates:
                    # If candidate was identified in master
                    problem_to_candidates[problem.name][
                        solver_var_info.name
                    ] = solver_var_info.column_id

        structure_str = ""
        for problem_name, candidate_to_index in problem_to_candidates.items():
            for candidate, index in candidate_to_index.items():
                structure_str += f"{problem_name:>50}{candidate:>50}{index:>10}\n"

        return structure_str

    def export_options(
        self, *, solver_name: str = "XPRESS", log_level: int = 0
    ) -> Dict[str, Any]:
        # Default values
        options_values = {
            "MAX_ITERATIONS": -1,
            "ABSOLUTE_GAP": 1,
            "RELATIVE_GAP": 1e-6,
            "RELAXED_GAP": 1e-5,
            "AGGREGATION": False,
            "OUTPUTROOT": ".",
            "TRACE": True,
            "SLAVE_WEIGHT": "CONSTANT",
            "SLAVE_WEIGHT_VALUE": 1,
            "MASTER_NAME": "master",
            "STRUCTURE_FILE": "structure.txt",
            "INPUTROOT": ".",
            "CSV_NAME": "benders_output_trace",
            "BOUND_ALPHA": True,
            "SEPARATION_PARAM": 0.5,
            "BATCH_SIZE": 0,
            "JSON_FILE": f"{self.output_path}/out.json",
            "LAST_ITERATION_JSON_FILE": f"{self.output_path}/last_iteration.json",
            "MASTER_FORMULATION": "integer",
            "SOLVER_NAME": solver_name,
            "TIME_LIMIT": 1_000_000_000_000,
            "LOG_LEVEL": log_level,
            "LAST_MASTER_MPS": "master_last_iteration",
            "LAST_MASTER_BASIS": "master_last_basis.bss",
        }
        return options_values

    def prepare(
        self,
        *,
        solver_name: str = "XPRESS",
        log_level: int = 0,
        is_debug: bool = False,
    ) -> None:
        serialize("master.mps", self.master.export_as_mps(), self.emplacement)
        for subproblem in self.subproblems:
            serialize(
                f"{subproblem.name}.mps", subproblem.export_as_mps(), self.emplacement
            )
        serialize("structure.txt", self.export_structure(), self.emplacement)
        serialize_json(
            "options.json",
            self.export_options(solver_name=solver_name, log_level=log_level),
            self.emplacement,
        )

        if is_debug:
            serialize("master.lp", self.master.export_as_lp(), self.emplacement)
            for subproblem in self.subproblems:
                serialize(
                    f"{subproblem.name}.lp", subproblem.export_as_lp(), self.emplacement
                )

    def read_solution(self) -> None:
        try:
            data = read_json("out.json", self.emplacement / self.output_path)

        except FileNotFoundError:
            # TODO For now, it will return as if nothing is wrong
            # modify it with runner's run
            print("Return without reading it for now")
            return

        if self.is_merged:
            self.solution = BendersMergedSolution(data)
        else:
            self.solution = BendersDecomposedSolution(data)

    def run(
        self,
        *,
        solver_name: str = "XPRESS",
        log_level: int = 0,
        should_merge: bool = False,
    ) -> bool:
        self.prepare(solver_name=solver_name, log_level=log_level)

        if not should_merge:
            return_code = BendersRunner(self.emplacement).run()
        else:
            self.is_merged = True
            return_code = MergeMPSRunner(self.emplacement).run()

        if return_code == 0:
            self.read_solution()
            return True
        else:
            return False


def build_benders_decomposed_problem(
    network_on_tree: Dict[TreeNode, Network],
    database: DataBase,
    configured_tree: ConfiguredTree,
    *,
    decision_coupling_model: Optional[Model] = None,
    border_management: BlockBorderManagement = BlockBorderManagement.CYCLE,
    solver_id: str = "GLOP",
) -> BendersDecomposedProblem:
    """
    Entry point to build the xpansion problem for a time period

    Returns a Benders Decomposed problem
    """

    master_network = create_master_network(network_on_tree, decision_coupling_model)

    # Benders Decomposed Master Problem
    master = build_problem(
        master_network,
        database,
        configured_tree.root,  # Could be any node, given the implmentation of get_nodes()
        null_time_block := TimeBlock(  # Not necessary for master, but list must be non-empty
            0, [0]
        ),
        null_scenario := 0,  # Not necessary for master
        problem_name="master",
        border_management=border_management,
        solver_id=solver_id,
        problem_strategy=InvestmentProblemStrategy(),
    )

    # Benders Decomposed Sub-problems
    subproblems = []
    for (
        tree_node,
        time_scenario_config,
    ) in configured_tree.node_to_config.items():
        for block in time_scenario_config.blocks:
            # Xpansion Sub-problems
            subproblems.append(
                build_problem(
                    network_on_tree[tree_node],
                    database,
                    block,
                    time_scenario_config.scenarios,
                    problem_name=f"subproblem_{tree_node.name}_{block.id}",
                    solver_id=solver_id,
                    problem_strategy=OperationalProblemStrategy(),
                )
            )

    return BendersDecomposedProblem(master, subproblems)
