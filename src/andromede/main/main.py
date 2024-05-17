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
from pathlib import Path
from typing import Optional

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


def input_models(model_path: Path) -> Library:
    with model_path.open() as lib:
        return resolve_library(parse_yaml_library(lib))


def input_database(study_path: Path, timeseries_path: Optional[Path]) -> DataBase:
    with study_path.open() as comp:
        return build_data_base(parse_yaml_components(comp), timeseries_path)


def input_components(study_path: Path, model: Library) -> NetworkComponents:
    with study_path.open() as comp:
        return resolve_components_and_cnx(parse_yaml_components(comp), model)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", type=Path, help="path to the model file, *.yml", required=True
    )
    parser.add_argument(
        "--study", type=Path, help="path to the study file, *.yml", required=True
    )
    parser.add_argument(
        "--timeseries", type=Path, help="path to the timeseries repertory"
    )
    parser.add_argument(
        "--duration", type=int, help="duration of the simulation", default=1
    )
    parser.add_argument(
        "--scenario", type=int, help="number of scenario of the simulation", default=1
    )

    args = parser.parse_args()

    models = input_models(args.model)
    components = input_components(args.study, models)
    consistency_check(components.components, models.models)

    try:
        database = input_database(args.study, args.timeseries)
    except UnboundLocalError:
        raise AntaresTimeSeriesImportError(
            "An error occurred while importing time series. Did you correctly use the '--timeseries' parameter ?"
        )
    network = build_network(components)

    for scenario in range(1, args.scenario + 1):
        timeblock = TimeBlock(1, list(range(args.duration)))
        try:
            problem = build_problem(network, database, timeblock, scenario)
        except IndexError as e:
            raise IndexError(
                str(e)
                + ". Did you correctly use the '--duration' and '--scenario' parameters ?"
            )

        status = problem.solver.Solve()
        print("scenario ", scenario)
        print("status : ", status)

    print("avarage final cost : ", problem.solver.Objective().Value())


if __name__ == "__main__":
    main()
