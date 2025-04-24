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
from typing import Dict

from pandas import DataFrame
from pypsa import Network

from andromede.pypsa_converter.utils import any_to_float
from andromede.study.parsing import (
    InputComponent,
    InputComponentParameter,
    InputPortConnections,
    InputSystem,
)


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

        self.components = {}
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
        pypsa_df: DataFrame,
        pypsa_dft: Dict[str, DataFrame],
        andromede_model: str,
        pypsa_params_to_andromede_params: Dict[str, str],
        pypsa_params_to_andromede_connections: Dict[str, tuple[str, str]],
    ) -> None:
        self.components[pypsa_model_id] = {
            "pypsa_df": pypsa_df,
            "pypsa_dft": pypsa_dft,
            "andromede_model": andromede_model,
            "pypsa_params_to_andromede_params": pypsa_params_to_andromede_params,
            "pypsa_params_to_andromede_connections": pypsa_params_to_andromede_connections,
        }

    def _convert(
        self, model_id: str
    ) -> tuple[list[InputComponent], list[InputPortConnections]]:
        components_from_model_id = self.components[model_id]
        return self._convert_pypsa_component(**components_from_model_id)

    def to_andromede_study(self) -> InputSystem:
        """Function"""

        self.logger.info("Study conversion started")
        list_components, list_connections = [], []

        for model_id in self.components:
            components, connections = self._convert(model_id)
            list_components.extend(components)
            list_connections.extend(connections)

        return InputSystem(
            nodes=[], components=list_components, connections=list_connections
        )

    def _convert_pypsa_component(
        self,
        pypsa_df: DataFrame,
        pypsa_dft: Dict[str, DataFrame],
        andromede_model: str,
        pypsa_params_to_andromede_params: Dict[str, str],
        pypsa_params_to_andromede_connections: Dict[str, tuple[str, str]],
    ) -> tuple[list[InputComponent], list[InputPortConnections]]:
        """
        Generic function to handle the different PyPSA classes
        pypsa_df: DataFrame : dataframe listing the components in the PyPSA class. Ex: pypsa_network.loads
        pypsa_dft: dict[DataFrame] : dictionnary of dataframe, one for each parameter or variable that is time-varying for some compoentns. Ex: pypsa_network.loads_t
        andromede_model: str : id of the model in the Andromede library
        pypsa_params_to_andromede_params: dict : for each parameter of the PyPSA class that is to be exported in the Andromede model as a parameter, the name of the corresponding parameter in the Andromede model
        pypsa_params_to_andromede_connections: dict, for each parameter of the PyPSA class that is to be exported in the Andromede model as a connection, a couple (model_port, bus_port)
        """

        self.logger.info(f"Creating objects of type: {andromede_model}. ")

        # We test wether the keys of the conversion dictionnary given in input concern
        assert set(pypsa_params_to_andromede_params).issubset(set(pypsa_df.columns))
        assert set(pypsa_params_to_andromede_connections).issubset(
            set(pypsa_df.columns)
        )

        # List of params and vars that may be time-dependant in the pypsa model
        pypsa_timedep = set(pypsa_dft.keys())

        # List of params that may be time-dependant in the pypsa model, among those we want to keep
        timedep_params = set(pypsa_params_to_andromede_params).intersection(
            pypsa_timedep
        )
        # Save time series and memorize the time-dependant parameters
        timedep_comp_param = dict()
        for param in timedep_params:
            timedf = pypsa_dft[param]
            for component in timedf.columns:
                tsname = self.system_name + "_" + component + "_" + param
                timedep_comp_param[(component, param)] = tsname
                timedf[[component]].to_csv(
                    self.series_dir / Path(tsname + ".txt"), index=False, header=False
                )

        connections, components = [], []

        for bus_id, couple in pypsa_params_to_andromede_connections.items():
            model_port, bus_port = couple
            buses = pypsa_df[bus_id].values
            for i, component in enumerate(pypsa_df.index):
                connections.append(
                    InputPortConnections(
                        component1=buses[i],
                        port1=bus_port,
                        component2=component,
                        port2=model_port,
                    )
                )

        for component in pypsa_df.index:
            components.append(
                InputComponent(
                    id=component,
                    model=f"{self.pypsalib_id}.{andromede_model}",
                    parameters=[
                        InputComponentParameter(
                            id=param,
                            time_dependent=(component, param) in timedep_comp_param,
                            scenario_dependent=False,
                            value=(
                                timedep_comp_param[(component, param)]
                                if (component, param) in timedep_comp_param
                                else any_to_float(pypsa_df.loc[component, param])
                            ),
                        )
                        for param in pypsa_params_to_andromede_params
                    ],
                )
            )
        return components, connections
