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

import json
import os
import pathlib
import subprocess
import sys
from typing import Any, Dict, List

from andromede.simulation.optimization import (
    BlockBorderManagement,
    OptimizationProblem,
    build_problem,
)
from andromede.simulation.strategy import (
    InvestmentProblemStrategy,
    OperationalProblemStrategy,
)
from andromede.simulation.time_block import TimeBlock
from andromede.study.data import DataBase
from andromede.study.network import Network
from andromede.utils import serialize


class BendersDecomposedProblem:
    """
    A simpler interface for the Benders Decomposed problem
    """

    master: OptimizationProblem
    subproblems: List[OptimizationProblem]

    def __init__(
        self, master: OptimizationProblem, subproblems: List[OptimizationProblem]
    ) -> None:
        self.master = master
        self.subproblems = subproblems

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
            "JSON_FILE": "output/xpansion/out.json",
            "LAST_ITERATION_JSON_FILE": "output/xpansion/last_iteration.json",
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
        path: str = "outputs/lp",
        solver_name: str = "XPRESS",
        log_level: int = 0,
        is_debug: bool = False,
    ) -> None:
        directory = pathlib.Path(path)
        serialize("master.mps", self.master.export_as_mps(), directory)
        serialize("subproblem.mps", self.subproblems[0].export_as_mps(), directory)
        serialize("structure.txt", self.export_structure(), directory)
        serialize(
            "options.json",
            json.dumps(
                self.export_options(solver_name=solver_name, log_level=log_level),
                indent=4,
            ),
            directory,
        )

        if is_debug:
            serialize("master.lp", self.master.export_as_lp(), directory)
            serialize("subproblem.lp", self.subproblems[0].export_as_lp(), directory)

    def run(
        self,
        *,
        path: str = "outputs/lp",
        solver_name: str = "XPRESS",
        log_level: int = 0,
    ) -> bool:
        self.prepare(path=path, solver_name=solver_name, log_level=log_level)
        root_dir = pathlib.Path().cwd()
        path_to_benders = root_dir / "bin" / "benders"

        if not path_to_benders.is_file():
            # TODO Maybe a more robust check and/or return value?
            # For now, it won't look anywhere else because a new
            # architecture should be discussed
            print(f"{path_to_benders} executable not found. Returning True")
            return True

        os.chdir(path)
        res = subprocess.run(
            [path_to_benders, "options.json"],
            stdout=sys.stdout,
            stderr=subprocess.DEVNULL,  # TODO For now, to avoid the "Invalid MIT-MAGIC-COOKIE-1 key" error
            shell=False,
        )
        os.chdir(root_dir)

        return res.returncode == 0


def build_benders_decomposed_problem(
    network: Network,
    database: DataBase,
    block: TimeBlock,
    scenarios: int,
    *,
    border_management: BlockBorderManagement = BlockBorderManagement.CYCLE,
    solver_id: str = "GLOP",
) -> BendersDecomposedProblem:
    """
    Entry point to build the xpansion problem for a time period

    Returns a Benders Decomposed problem
    """

    # Benders Decomposed Master Problem
    master = build_problem(
        network,
        database,
        block,
        scenarios,
        problem_name="master",
        border_management=border_management,
        solver_id=solver_id,
        problem_strategy=InvestmentProblemStrategy(),
    )

    # Benders Decomposed Sub-problems
    subproblem = build_problem(
        network,
        database,
        block,
        scenarios,
        problem_name="subproblem",
        border_management=border_management,
        solver_id=solver_id,
        problem_strategy=OperationalProblemStrategy(),
    )

    return BendersDecomposedProblem(master, [subproblem])
