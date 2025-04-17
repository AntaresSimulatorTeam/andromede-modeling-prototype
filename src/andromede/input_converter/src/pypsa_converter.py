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
from typing import Optional


from pandas import DataFrame


from andromede.study.parsing import (
    InputComponent,
    InputComponentParameter,
    InputPortConnections,
    InputSystem,
)
from pypsa import Network


class PyPSAStudyConverter:
    def __init__(
        self,
        pypsa_network: Network,
        logger: logging.Logger,
        system_dir: Optional[Path] = None,
        series_dir: Optional[Path] = None,
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

    def __convert_pypsa_class(
        self,
        pypsa_df: DataFrame,
        pypsa_dft: DataFrame,
        andromede_model: str,
        pypsa_params_to_andromede_params: dict,
        pypsa_params_to_andromede_connections: dict,
    ):
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

        timedep_comp_param = dict()

        # Save time series and register
        for param in timedep_params:
            timedf = pypsa_dft[param]
            for component in timedf.columns:
                tsname = self.system_name + "_" + component + "_" + param
                timedep_comp_param[(component, param)] = tsname
                timedf[[component]].to_csv(
                    self.series_dir / Path(tsname + ".txt"), index=False, header=False
                )

        connections, components = [], []
        if len(pypsa_params_to_andromede_connections) > 0:
            for bus, model_port in pypsa_params_to_andromede_connections.items():
                assert model_port != None
                buses = pypsa_df[bus].values
                for i, component in enumerate(pypsa_df.index):
                    connections.append(
                        InputPortConnections(
                            component1=buses[i],
                            port1="p_balance_port",
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
                                else pypsa_df.loc[component, param]
                            ),
                        )
                        for param in pypsa_params_to_andromede_params
                    ],
                )
            )
        return components, connections

    def __convert_pypsa_buses(self):
        return self.__convert_pypsa_class(
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

    def __convert_pypsa_loads(self):
        return self.__convert_pypsa_class(
            self.pypsa_network.loads,
            self.pypsa_network.loads_t,
            "load",
            {
                "p_set": "p_set",
                "q_set": "q_set",
                "sign": "sign",
                "active": "active",
            },
            {"bus": "p_balance_port"},
        )

    def __convert_pypsa_generatorsv0(self):
        return self.__convert_pypsa_class(
            self.pypsa_network.generators,
            self.pypsa_network.generators_t,
            "generator_v0",
            {
                "p_nom": "p_nom",
                "marginal_cost": "marginal_cost",
            },
            {"bus": "p_balance_port"},
        )

    def __convert_pypsa_generators(self):
        print(
            "To be implemented, calling self.__convert_pypsa_class() with the right parameters"
        )

    def __convert_pypsa_links(self):
        print(
            "To be implemented, calling self.__convert_pypsa_class() with the right parameters"
        )
        "The dictionnary pypsa_params_to_andromede_connections will have the form bus0: out_port, bus1:in_port... or the reverse!"

    def __convert_pypsa_stores(self):
        print(
            "To be implemented, calling self.__convert_pypsa_class() with the right parameters"
        )

    def __convert_pypsa_storage(self):
        print(
            "To be implemented, calling self.__convert_pypsa_class() with the right parameters"
        )

    def to_andromede_study(self) -> InputSystem:
        """Function"""

        self.logger.info("Study conversion started")
        list_components, list_connections = [], []
        methods = [
            self.__convert_pypsa_buses,
            self.__convert_pypsa_loads,
            self.__convert_pypsa_generatorsv0,
        ]

        for method in methods:
            components, connections = method()
            list_components.extend(components)
            list_connections.extend(connections)

        return InputSystem(
            nodes=[], components=list_components, connections=list_connections
        )
