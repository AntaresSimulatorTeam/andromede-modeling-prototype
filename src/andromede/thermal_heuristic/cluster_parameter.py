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


import pandas as pd

from andromede.study import (
    ConstantData,
    DataBase,
    TimeIndex,
    TimeScenarioSeriesData,
    TimeSeriesData,
)
from andromede.study.data import ComponentParameterIndex
from andromede.thermal_heuristic.data import (
    get_max_failures,
    get_max_unit,
    get_max_unit_for_min_down_time,
)
from andromede.thermal_heuristic.time_scenario_parameter import (
    TimeScenarioHourParameter,
    WeekScenarioIndex,
    timesteps,
)


def compute_delta(thermal_cluster: str, database: DataBase) -> int:
    delta = int(
        max(
            database.get_value(
                ComponentParameterIndex(thermal_cluster, "d_min_up"), 0, 0
            ),
            database.get_value(
                ComponentParameterIndex(thermal_cluster, "d_min_down"), 0, 0
            ),
        )
    )
    return delta


def complete_database_for_fast_heuristic(
    database: DataBase,
    list_cluster_id: list[str],
    time_scenario_hour_parameter: TimeScenarioHourParameter,
) -> None:
    for cluster_id in list_cluster_id:
        delta = compute_delta(cluster_id, database)
        n_max = database.get_data(cluster_id, "nb_units_max").get_max_value()
        database.add_data(cluster_id, "n_max", ConstantData(int(n_max)))
        database.add_data(cluster_id, "delta", ConstantData(delta))

        for h in range(delta):
            start_ajust = time_scenario_hour_parameter.hour - delta + h
            database.add_data(
                cluster_id,
                f"alpha_ajust_{h}",
                TimeSeriesData(
                    {
                        TimeIndex(t): (
                            1
                            if (t % time_scenario_hour_parameter.hour >= start_ajust)
                            or (t % time_scenario_hour_parameter.hour < h)
                            else 0
                        )
                        for t in range(
                            time_scenario_hour_parameter.hour
                            * time_scenario_hour_parameter.week
                        )
                    }
                ),
            )
            for k in range(time_scenario_hour_parameter.hour // delta):
                start_k = k * delta + h
                end_k = min(start_ajust, (k + 1) * delta + h)
                database.add_data(
                    cluster_id,
                    f"alpha_{k}_{h}",
                    TimeSeriesData(
                        {
                            TimeIndex(t): (
                                1
                                if (t % time_scenario_hour_parameter.hour >= start_k)
                                and (t % time_scenario_hour_parameter.hour < end_k)
                                else 0
                            )
                            for t in range(
                                time_scenario_hour_parameter.hour
                                * time_scenario_hour_parameter.week
                            )
                        }
                    ),
                )


def complete_database_with_cluster_parameters(
    database: DataBase,
    list_cluster: list[str],
    time_scenario_hour_parameter: TimeScenarioHourParameter,
) -> None:
    for cluster_id in list_cluster:
        if type(database.get_data(cluster_id, "max_generating")) is ConstantData:
            database.add_data(
                cluster_id,
                "max_failure",
                ConstantData(0),
            )
            database.add_data(
                cluster_id,
                "nb_units_max_min_down_time",
                database.get_data(cluster_id, "nb_units_max"),
            )

        else:
            (
                max_units,
                max_failures,
                nb_units_max_min_down_time,
            ) = compute_cluster_parameters(
                database,
                cluster_id,
                time_scenario_hour_parameter,
            )
            database.add_data(
                cluster_id,
                "nb_units_max",
                TimeScenarioSeriesData(max_units),
            )
            database.add_data(
                cluster_id,
                "max_failure",
                TimeScenarioSeriesData(max_failures),
            )
            database.add_data(
                cluster_id,
                "nb_units_max_min_down_time",
                TimeScenarioSeriesData(nb_units_max_min_down_time),
            )


def compute_cluster_parameters(
    database: DataBase,
    cluster_id: str,
    time_scenario_hour_parameter: TimeScenarioHourParameter,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    database.convert_to_time_scenario_series_data(
        ComponentParameterIndex(cluster_id, "max_generating"),
        timesteps=time_scenario_hour_parameter.hour * time_scenario_hour_parameter.week,
        scenarios=time_scenario_hour_parameter.scenario,
    )
    max_units = get_max_unit(
        database.get_value(ComponentParameterIndex(cluster_id, "p_max"), 0, 0),
        database.get_value(ComponentParameterIndex(cluster_id, "nb_units_max"), 0, 0),
        database.get_data(
            cluster_id, "max_generating"
        ).time_scenario_series,  # type:ignore
    )
    max_failures = get_max_failures(max_units, time_scenario_hour_parameter.hour)
    nb_units_max_min_down_time = get_max_unit_for_min_down_time(
        int(
            max(
                database.get_value(
                    ComponentParameterIndex(cluster_id, "d_min_up"), 0, 0
                ),
                database.get_value(
                    ComponentParameterIndex(cluster_id, "d_min_down"), 0, 0
                ),
            )
        ),
        max_units,
        time_scenario_hour_parameter.hour,
    )

    return max_units, max_failures, nb_units_max_min_down_time


def get_parameter(
    database: DataBase,
    name: str,
    component: str,
    index: WeekScenarioIndex,
    time_scenario_hour_parameter: TimeScenarioHourParameter,
) -> list[float]:
    return [
        database.get_value(
            ComponentParameterIndex(component, name),
            t,
            index.scenario,
        )
        for t in timesteps(index, time_scenario_hour_parameter)
    ]
