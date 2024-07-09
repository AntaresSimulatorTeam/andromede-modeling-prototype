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

from pathlib import Path

import pandas as pd
import pytest

from andromede.libs.standard import (
    DEMAND_MODEL,
    LINK_MODEL,
    NODE_WITH_SPILL_AND_ENS,
    RES_MODEL,
    THERMAL_CLUSTER_MODEL_FAST,
)
from andromede.study.data import ConstantData, DataBase, TimeScenarioSeriesData
from andromede.study.network import Network, Node, PortRef, create_component


@pytest.fixture
def network() -> Network:
    network = Network("test_case")

    # Area 1
    area1 = Node(model=NODE_WITH_SPILL_AND_ENS, id="Area1")
    load1 = create_component(model=DEMAND_MODEL, id="D1")
    wind1 = create_component(model=RES_MODEL, id="Wind1")
    base1 = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="Base1")
    semi1 = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="SemiBase1")
    peak1 = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="Peak1")

    network.add_node(area1)
    network.add_component(load1)
    network.add_component(wind1)
    network.add_component(base1)
    network.add_component(semi1)
    network.add_component(peak1)
    network.connect(PortRef(load1, "balance_port"), PortRef(area1, "balance_port"))
    network.connect(PortRef(wind1, "balance_port"), PortRef(area1, "balance_port"))
    network.connect(PortRef(base1, "balance_port"), PortRef(area1, "balance_port"))
    network.connect(PortRef(semi1, "balance_port"), PortRef(area1, "balance_port"))
    network.connect(PortRef(peak1, "balance_port"), PortRef(area1, "balance_port"))

    # Area 2
    area2 = Node(model=NODE_WITH_SPILL_AND_ENS, id="Area2")
    load2 = create_component(model=DEMAND_MODEL, id="D2")
    wind2 = create_component(model=RES_MODEL, id="Wind2")
    base2 = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="Base2")
    semi2 = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="SemiBase2")
    peak2 = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="Peak2")

    network.add_node(area2)
    network.add_component(load2)
    network.add_component(wind2)
    network.add_component(base2)
    network.add_component(semi2)
    network.add_component(peak2)
    network.connect(PortRef(load2, "balance_port"), PortRef(area2, "balance_port"))
    network.connect(PortRef(wind2, "balance_port"), PortRef(area2, "balance_port"))
    network.connect(PortRef(base2, "balance_port"), PortRef(area2, "balance_port"))
    network.connect(PortRef(semi2, "balance_port"), PortRef(area2, "balance_port"))
    network.connect(PortRef(peak2, "balance_port"), PortRef(area2, "balance_port"))

    # Link
    link12 = create_component(model=LINK_MODEL, id="Area1/Area2")
    network.connect(
        PortRef(link12, "balance_port_from"), PortRef(area1, "balance_port")
    )
    network.connect(PortRef(link12, "balance_port_to"), PortRef(area2, "balance_port"))

    # Candidates
    cand_peak = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="Cand_Peak")
    cand_semi = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="Cand_Semi")

    network.add_component(cand_peak)
    network.add_component(cand_semi)
    network.connect(PortRef(cand_peak, "balance_port"), PortRef(area1, "balance_port"))
    network.connect(PortRef(cand_semi, "balance_port"), PortRef(area1, "balance_port"))

    return network


@pytest.fixture
def database() -> DataBase:
    path = Path("tests/functional/data/pathway_test_case/")
    ts_len = 1  # 24 * 7 * 2 - 1 # Two weeks

    wind = pd.merge(
        left=pd.read_csv(
            path / Path("wind_area1.txt"), sep="\s+", names=["TS1", "TS2"]
        ),
        right=pd.read_csv(
            path / Path("wind_area2.txt"), sep="\s+", names=["TS1", "TS2"]
        ),
        left_index=True,
        right_index=True,
        suffixes=("_Area1", "_Area2"),
    )

    load = pd.merge(
        left=pd.read_csv(
            path / Path("load_area1.txt"), sep="\s+", names=["TS1", "TS2"]
        ),
        right=pd.read_csv(
            path / Path("load_area2.txt"), sep="\s+", names=["TS1", "TS2"]
        ),
        left_index=True,
        right_index=True,
        suffixes=("_Area1", "_Area2"),
    )

    database = DataBase()

    # Area 1
    database.add_data("Area1", "spillage_cost", ConstantData(0))
    database.add_data("Area1", "ens_cost", ConstantData(20_000))

    database.add_data(
        "D1",
        "demand",
        TimeScenarioSeriesData.from_dataframe(
            load.loc[:ts_len, "TS1_Area1":"TS2_Area1"]
        ),
    )
    database.add_data(
        "Wind1",
        "production",
        TimeScenarioSeriesData.from_dataframe(
            wind.loc[:ts_len, "TS1_Area1":"TS2_Area1"]
        ),
    )

    database.add_data("Base1", "p_max", ConstantData(900))
    database.add_data("Base1", "nb_units_max", ConstantData(3))
    database.add_data("Base1", "cost", ConstantData(20))
    database.add_data("Base1", "mingen", ConstantData(0))
    database.add_data("Base1", "failures", ConstantData(3 * 900))

    database.add_data("Peak1", "p_max", ConstantData(100))
    database.add_data("Peak1", "nb_units_max", ConstantData(10))
    database.add_data("Peak1", "cost", ConstantData(100))
    database.add_data("Peak1", "mingen", ConstantData(0))
    database.add_data("Peak1", "failures", ConstantData(10 * 100))

    database.add_data("SemiBase1", "p_max", ConstantData(450))
    database.add_data("SemiBase1", "nb_units_max", ConstantData(2))
    database.add_data("SemiBase1", "cost", ConstantData(45))
    database.add_data("SemiBase1", "mingen", ConstantData(0))
    database.add_data("SemiBase1", "failures", ConstantData(2 * 450))

    # Area 2
    database.add_data("Area2", "spillage_cost", ConstantData(0))
    database.add_data("Area2", "ens_cost", ConstantData(20_000))

    database.add_data(
        "D2",
        "demand",
        TimeScenarioSeriesData.from_dataframe(
            load.loc[:ts_len, "TS1_Area2":"TS2_Area2"]
        ),
    )
    database.add_data(
        "Wind2",
        "production",
        TimeScenarioSeriesData.from_dataframe(
            wind.loc[:ts_len, "TS1_Area2":"TS2_Area2"]
        ),
    )

    database.add_data("Base2", "p_max", ConstantData(900))
    database.add_data("Base2", "nb_units_max", ConstantData(3))
    database.add_data("Base2", "cost", ConstantData(20))
    database.add_data("Base2", "mingen", ConstantData(0))
    database.add_data("Base2", "failures", ConstantData(3 * 900))

    database.add_data("Peak2", "p_max", ConstantData(100))
    database.add_data("Peak2", "nb_units_max", ConstantData(2))
    database.add_data("Peak2", "cost", ConstantData(100))
    database.add_data("Peak2", "mingen", ConstantData(0))
    database.add_data("Peak2", "failures", ConstantData(2 * 100))

    database.add_data("SemiBase2", "p_max", ConstantData(450))
    database.add_data("SemiBase2", "nb_units_max", ConstantData(2))
    database.add_data("SemiBase2", "cost", ConstantData(45))
    database.add_data("SemiBase2", "mingen", ConstantData(0))
    database.add_data("SemiBase2", "failures", ConstantData(2 * 450))

    # Link
    database.add_data("Area1/Area2", "f_max", ConstantData(1_000))

    # Candidates
    database.add_data("Cand_Peak", "p_max", ConstantData(100))
    database.add_data("Cand_Peak", "nb_units_max", ConstantData(1))
    database.add_data("Cand_Peak", "cost", ConstantData(180))
    database.add_data("Cand_Peak", "mingen", ConstantData(0))
    database.add_data("Cand_Peak", "failures", ConstantData(1 * 100))

    database.add_data("Cand_Semi", "p_max", ConstantData(200))
    database.add_data("Cand_Semi", "nb_units_max", ConstantData(10))
    database.add_data("Cand_Semi", "cost", ConstantData(50))
    database.add_data("Cand_Semi", "mingen", ConstantData(0))
    database.add_data("Cand_Semi", "failures", ConstantData(10 * 200))

    return database


def test_single_investment_node(network: Network, database: DataBase) -> None:
    return
