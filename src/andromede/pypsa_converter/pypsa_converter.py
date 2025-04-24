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
import logging
from pathlib import Path
from typing import Union

import pandas as pd
from pypsa import Network

from andromede.pypsa_converter.utils import any_to_float
from andromede.study.parsing import (
    InputComponent,
    InputComponentParameter,
    InputPortConnections,
    InputSystem,
)


def check_pypsa_params_consistency(
    pypsa_params: Union[dict[str, str], dict[str, tuple[str, str]]],
    data: pd.DataFrame,
) -> None:
    for key in pypsa_params:
        if key not in data.columns:
            raise ValueError(f"Parameter {key} not available in data")


class PyPSAStudyConverter:
    def __init__(
        self,
        pypsa_network: Network,
        logger: logging.Logger,
        system_dir: Path,
        series_dir: Path,
    ):
        """
        Initialize processor
        """
        self.logger = logger
        self.system_dir = system_dir
        self.series_dir = series_dir
        self.pypsa_network = pypsa_network
        self.pypsalib_id = "pypsa_models"
        self.system_name = pypsa_network.name

        self.model_to_components: dict[str, dict] = {}
        self._set_pypsa_models()

        assert len(pypsa_network.investment_periods) == 0

    def _set_pypsa_models(self) -> None:
        self._register_pypsa_model(
            "generatorsv0",
            self.pypsa_network.generators,
            self.pypsa_network.generators_t,
            "generator_v0",
            {
                "p_nom": "p_nom",
                "marginal_cost": "marginal_cost",
            },
            {"bus": ("p_balance_port", "p_balance_port")},
        )
        self._register_pypsa_model(
            "loads",
            self.pypsa_network.loads,
            self.pypsa_network.loads_t,
            "load",
            {
                "p_set": "p_set",
                "q_set": "q_set",
                "sign": "sign",
                "active": "active",
            },
            {"bus": ("p_balance_port", "p_balance_port")},
        )
        self._register_pypsa_model(
            "buses",
            self.pypsa_network.buses,
            self.pypsa_network.buses_t,
            "bus",
            {
                "v_nom": "v_nom",
                "x": "x",
                "y": "y",
                "v_mag_pu_set": "v_mag_pu_set",
                "v_mag_pu_min": "v_mag_pu_min",
                "v_mag_pu_max": "v_mag_pu_max",
            },
            {},
        )
        self._register_pypsa_model(
            "links",
            self.pypsa_network.links,
            self.pypsa_network.links_t,
            "link",
            {
                "efficiency": "efficiency",
                "active": "active",
                "p_nom": "p_nom",
                "p_min_pu": "p_min_pu",
                "p_max_pu": "p_max_pu",
                "marginal_cost": "marginal_cost",
            },
            {
                "bus0": ("p0_port", "p_balance_port"),
                "bus1": ("p1_port", "p_balance_port"),
            },
        )
        # TODO: Stoers, storages, global_constraints
        # self._register_pypsa_model("stores")
        # self._register_pypsa_model("storage_units")
        # self._register_pypsa_model("global_constraints")

    def _register_pypsa_model(
        self,
        pypsa_model_id: str,
        constant_data: pd.DataFrame,
        time_dependent_data: dict[str, pd.DataFrame],
        andromede_model_id: str,
        pypsa_params_to_andromede_params: dict[str, str],
        pypsa_params_to_andromede_connections: dict[str, tuple[str, str]],
    ) -> None:
        if pypsa_model_id in self.model_to_components:
            raise ValueError(f"{pypsa_model_id} already registered !")

        self.model_to_components[pypsa_model_id] = {
            "constant_data": constant_data,
            "time_dependent_data": time_dependent_data,
            "andromede_model_id": andromede_model_id,
            "pypsa_params_to_andromede_params": pypsa_params_to_andromede_params,
            "pypsa_params_to_andromede_connections": pypsa_params_to_andromede_connections,
        }

    def _convert(
        self, model_id: str
    ) -> tuple[list[InputComponent], list[InputPortConnections]]:
        components_from_model_id = self.model_to_components[model_id]
        return self._convert_pypsa_components_of_given_model(**components_from_model_id)

    def to_andromede_study(self) -> InputSystem:
        """Function"""

        self.logger.info("Study conversion started")
        list_components, list_connections = [], []

        for model_id in self.model_to_components:
            components, connections = self._convert(model_id)
            list_components.extend(components)
            list_connections.extend(connections)

        return InputSystem(
            nodes=[], components=list_components, connections=list_connections
        )

    def _convert_pypsa_components_of_given_model(
        self,
        constant_data: pd.DataFrame,
        time_dependent_data: dict[str, pd.DataFrame],
        andromede_model_id: str,
        pypsa_params_to_andromede_params: dict[str, str],
        pypsa_params_to_andromede_connections: dict[str, tuple[str, str]],
    ) -> tuple[list[InputComponent], list[InputPortConnections]]:
        """
        Generic function to handle the different PyPSA classes

        Parameters
        -----------
        constant_data: pd.DataFrame
            Dataframe listing the components in the PyPSA class. Ex: pypsa_network.loads
        time_dependent_data: dict[str, pd.DataFrame]
            Dictionary of dataframe, one for each parameter or variable that is time-varying for some compoentns. Ex: pypsa_network.loads_t
        andromede_model_id: str
            Id of the model in the Andromede library
        pypsa_params_to_andromede_params: dict
            For each parameter of the PyPSA class that is to be exported in the Andromede model as a parameter, the name of the corresponding parameter in the Andromede model
        pypsa_params_to_andromede_connections: dict
            For each parameter of the PyPSA class that is to be exported in the Andromede model as a connection, a couple (model_port, bus_port)

        Returns
        ----------
        tuple[list[InputComponent], list[InputPortConnections]]
            A tuple containing the list of InputComponent and the list of InputPortConnections that represent the PyPSA components in the modeler format
        """

        self.logger.info(f"Creating objects of type: {andromede_model_id}. ")

        # We test whether the keys of the conversion dictionary are allowed in the PyPSA model : all authorized parameters are columns in the constant data frame (even though they are specified as time-varying values in the time-varying data frame)
        check_pypsa_params_consistency(pypsa_params_to_andromede_params, constant_data)
        check_pypsa_params_consistency(
            pypsa_params_to_andromede_connections, constant_data
        )

        # List of params that may be time-dependent in the pypsa model, among those we want to keep
        time_dependent_params = set(pypsa_params_to_andromede_params).intersection(
            set(time_dependent_data.keys())
        )
        # Save time series and memorize the time-dependent parameters
        comp_param_to_timeseries_name = self._write_and_register_timeseries(
            time_dependent_data, time_dependent_params
        )

        connections = self._create_andromede_connections(
            constant_data, pypsa_params_to_andromede_connections
        )

        components = self._create_andromede_components(
            constant_data,
            andromede_model_id,
            pypsa_params_to_andromede_params,
            comp_param_to_timeseries_name,
        )
        return components, connections

    def _write_and_register_timeseries(
        self,
        time_dependent_data: dict[str, pd.DataFrame],
        time_dependent_params: set[str],
    ) -> dict[tuple[str, str], str]:
        comp_param_to_timeseries_name = dict()
        for param in time_dependent_params:
            param_df = time_dependent_data[param]
            for component in param_df.columns:
                timeseries_name = self.system_name + "_" + component + "_" + param
                comp_param_to_timeseries_name[(component, param)] = timeseries_name
                param_df[[component]].to_csv(
                    self.series_dir / Path(timeseries_name + ".txt"),
                    index=False,
                    header=False,
                )

        return comp_param_to_timeseries_name

    def _create_andromede_components(
        self,
        constant_data: pd.DataFrame,
        andromede_model_id: str,
        pypsa_params_to_andromede_params: dict[str, str],
        comp_param_to_timeseries_name: dict[tuple[str, str], str],
    ) -> list[InputComponent]:
        components = []
        for component in constant_data.index:
            components.append(
                InputComponent(
                    id=component,
                    model=f"{self.pypsalib_id}.{andromede_model_id}",
                    parameters=[
                        InputComponentParameter(
                            id=param,
                            time_dependent=(component, param)
                            in comp_param_to_timeseries_name,
                            scenario_dependent=False,
                            value=(
                                comp_param_to_timeseries_name[(component, param)]
                                if (component, param) in comp_param_to_timeseries_name
                                else any_to_float(constant_data.loc[component, param])
                            ),
                        )
                        for param in pypsa_params_to_andromede_params
                    ],
                )
            )
        return components

    def _create_andromede_connections(
        self,
        constant_data: pd.DataFrame,
        pypsa_params_to_andromede_connections: dict[str, tuple[str, str]],
    ) -> list[InputPortConnections]:
        connections = []
        for bus_id, (
            model_port,
            bus_port,
        ) in pypsa_params_to_andromede_connections.items():
            buses = constant_data[bus_id].values
            for component_id, component in enumerate(constant_data.index):
                connections.append(
                    InputPortConnections(
                        component1=buses[component_id],
                        port1=bus_port,
                        component2=component,
                        port2=model_port,
                    )
                )
        return connections
