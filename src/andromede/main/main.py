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
import argparse
from os import listdir
from pathlib import Path
from typing import List, Optional

from andromede.model.library import Library
from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation import OutputValues, TimeBlock, build_problem
from andromede.study import DataBase
from andromede.study.parsing import parse_yaml_components
from andromede.study.resolve_components import (
    NetworkComponents,
    build_data_base,
    build_network,
    consistency_check,
    resolve_components_and_cnx,
)


class AntaresTimeSeriesImportError(Exception):
    pass


def input_models(model_paths: List[Path]) -> Library:
    yaml_libraries = []
    yaml_library_ids = set()
    for path in model_paths:
        with path.open("r") as file:
            yaml_lib = parse_yaml_library(file)
            if yaml_lib.id in yaml_library_ids:
                raise ValueError(f"the identifier: {yaml_lib.id} is defined twice")
            yaml_libraries.append(yaml_lib)
            yaml_library_ids.add(yaml_lib.id)

    return resolve_library(yaml_libraries)


def input_database(study_path: Path, timeseries_path: Optional[Path]) -> DataBase:
    with study_path.open() as comp:
        return build_data_base(parse_yaml_components(comp), timeseries_path)


def input_components(study_path: Path, model: Library) -> NetworkComponents:
    with study_path.open() as comp:
        return resolve_components_and_cnx(parse_yaml_components(comp), model)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--study", type=Path, help="path to the root directory of the study"
    )
    parser.add_argument(
        "--models", nargs="+", type=Path, help="list of path to model file, *.yml"
    )
    parser.add_argument(
        "--component", type=Path, help="path to the component file, *.yml"
    )
    parser.add_argument(
        "--timeseries", type=Path, help="path to the timeseries directory"
    )
    parser.add_argument(
        "--duration", type=int, help="duration of the simulation", default=1
    )
    parser.add_argument(
        "--scenario", type=int, help="number of scenario of the simulation", default=1
    )

    args = parser.parse_args()

    components = None
    database = None

    if args.study:
        if args.models or args.component or args.timeseries:
            parser.error(
                "--study flag can't be use with --models, --component and --timeseries"
            )
        components_path = args.study / "input" / "components" / "components.yml"
        timeseries_dir = args.study / "input" / "components" / "series"
        model_paths = [
            args.study / "input" / "models" / file
            for file in listdir(args.study / "input" / "models")
        ]

        models = input_models(model_paths)
        components = input_components(components_path, models)
        consistency_check(components.components, models.models)
        try:
            database = input_database(components_path, timeseries_dir)
        except UnboundLocalError:
            raise AntaresTimeSeriesImportError(
                f"An error occurred while importing time series. Are all timeseries files in {timeseries_dir} ?"
            )

    else:
        if not args.models or not args.component:
            parser.error("--models and --component must be entered")

        models = input_models(args.models)
        components = input_components(args.component, models)
        consistency_check(components.components, models.models)

        try:
            database = input_database(args.component, args.timeseries)
        except UnboundLocalError:
            raise AntaresTimeSeriesImportError(
                "An error occurred while importing time series. Did you correctly use the '--timeseries' parameter ?"
            )

    network = build_network(components)

    timeblock = TimeBlock(1, list(range(args.duration)))
    scenario = args.scenario
    try:
        problem = build_problem(network, database, timeblock, scenario)
    except IndexError as e:
        raise IndexError(
            str(e)
            + ". Did you correctly use the '--duration' and '--scenario' parameters ?"
        )

    status = problem.solver.Solve()
    print("status : ", status)

    print("final average cost : ", problem.solver.Objective().Value())


if __name__ == "__main__":
    main()
