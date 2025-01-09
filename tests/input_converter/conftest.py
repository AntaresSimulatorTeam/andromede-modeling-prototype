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
import pytest
from antares.craft.model.area import Area, AreaPropertiesLocal
from antares.craft.model.binding_constraint import (
    BindingConstraint,
    BindingConstraintFrequency,
    BindingConstraintOperator,
    BindingConstraintProperties,
)
from antares.craft.model.hydro import HydroProperties
from antares.craft.model.renewable import (
    RenewableClusterGroup,
    RenewableClusterProperties,
    TimeSeriesInterpretation,
)
from antares.craft.model.st_storage import STStorageGroup, STStorageProperties
from antares.craft.model.study import Study, create_study_local
from antares.craft.model.thermal import (
    LawOption,
    LocalTSGenerationBehavior,
    ThermalClusterGroup,
    ThermalClusterProperties,
    ThermalCostGeneration,
)
from antares.craft.tools.ini_tool import IniFile, IniFileTypes


@pytest.fixture
def local_study(tmp_path) -> Study:
    study_name = "studyTest"
    study_version = "880"
    return create_study_local(study_name, study_version, str(tmp_path.absolute()))


@pytest.fixture
def local_study_w_areas(tmp_path, local_study) -> Study:
    areas_to_create = ["fr", "it"]
    for area in areas_to_create:
        area_properties = AreaPropertiesLocal(
            energy_cost_spilled="1.0", energy_cost_unsupplied="1.5"
        )
        local_study.create_area(area, properties=area_properties)
    return local_study


@pytest.fixture
def local_study_w_links(tmp_path, local_study_w_areas):
    local_study_w_areas.create_area("at")
    links_to_create = ["fr_at", "at_it", "fr_it"]
    for link in links_to_create:
        area_from, area_to = link.split("_")
        local_study_w_areas.create_link(area_from=area_from, area_to=area_to)

    return local_study_w_areas


@pytest.fixture
def local_study_w_thermal(tmp_path, local_study_w_links) -> Study:
    thermal_name = "gaz"
    local_study_w_links.get_areas()["fr"].create_thermal_cluster(thermal_name)
    return local_study_w_links


@pytest.fixture
def default_thermal_cluster_properties() -> ThermalClusterProperties:
    return ThermalClusterProperties(
        group=ThermalClusterGroup.OTHER1,
        enabled=True,
        unit_count=1,
        nominal_capacity=0,
        gen_ts=LocalTSGenerationBehavior.USE_GLOBAL,
        min_stable_power=0,
        min_up_time=1,
        min_down_time=1,
        must_run=False,
        spinning=0,
        volatility_forced=0,
        volatility_planned=0,
        law_forced=LawOption.UNIFORM,
        law_planned=LawOption.UNIFORM,
        marginal_cost=0,
        spread_cost=0,
        fixed_cost=0,
        startup_cost=0,
        market_bid_cost=0,
        co2=0,
        nh3=0,
        so2=0,
        nox=0,
        pm2_5=0,
        pm5=0,
        pm10=0,
        nmvoc=0,
        op1=0,
        op2=0,
        op3=0,
        op4=0,
        op5=0,
        cost_generation=ThermalCostGeneration.SET_MANUALLY,
        efficiency=100,
        variable_o_m_cost=0,
    )


@pytest.fixture
def actual_thermal_list_ini(local_study_w_thermal) -> IniFile:
    return IniFile(
        local_study_w_thermal.service.config.study_path,
        IniFileTypes.THERMAL_LIST_INI,
        area_id="fr",
    )


@pytest.fixture
def actual_thermal_areas_ini(local_study_w_thermal) -> IniFile:
    return IniFile(
        local_study_w_thermal.service.config.study_path, IniFileTypes.THERMAL_AREAS_INI
    )


@pytest.fixture
def actual_adequacy_patch_ini(local_study_w_areas) -> IniFile:
    return IniFile(
        local_study_w_areas.service.config.study_path,
        IniFileTypes.AREA_ADEQUACY_PATCH_INI,
        area_id="fr",
    )


@pytest.fixture
def local_study_with_renewable(local_study_w_thermal) -> Study:
    renewable_cluster_name = "generation"
    time_serie = pd.DataFrame(
        [
            [-9999999980506447872, 0, 9999999980506447872],
            [0, "fr", 0],
        ],
        dtype="object",
    )
    local_study_w_thermal.get_areas()["fr"].create_renewable_cluster(
        renewable_cluster_name, RenewableClusterProperties(), series=time_serie
    )
    return local_study_w_thermal


@pytest.fixture
def default_renewable_cluster_properties() -> RenewableClusterProperties:
    return RenewableClusterProperties(
        enabled=True,
        unit_count=1,
        nominal_capacity=0,
        group=RenewableClusterGroup.OTHER1,
        ts_interpretation=TimeSeriesInterpretation.POWER_GENERATION,
    )


@pytest.fixture
def actual_renewable_list_ini(local_study_with_renewable) -> IniFile:
    return IniFile(
        local_study_with_renewable.service.config.study_path,
        IniFileTypes.RENEWABLES_LIST_INI,
        area_id="fr",
    )


@pytest.fixture
def local_study_with_st_storage(local_study_with_renewable) -> Study:
    storage_name = "short term storage"
    local_study_with_renewable.get_areas()["fr"].create_st_storage(storage_name)
    return local_study_with_renewable


@pytest.fixture
def default_st_storage_properties() -> STStorageProperties:
    return STStorageProperties(
        group=STStorageGroup.OTHER1,
        injection_nominal_capacity=0,
        withdrawal_nominal_capacity=0,
        reservoir_capacity=0,
        efficiency=1,
        initial_level=0.5,
        initial_level_optim=False,
        enabled=True,
    )


@pytest.fixture
def actual_st_storage_list_ini(local_study_with_st_storage) -> IniFile:
    return IniFile(
        local_study_with_st_storage.service.config.study_path,
        IniFileTypes.ST_STORAGE_LIST_INI,
        area_id="fr",
    )


@pytest.fixture
def local_study_with_hydro(local_study_with_st_storage) -> Study:
    local_study_with_st_storage.get_areas()["fr"].create_hydro()
    return local_study_with_st_storage


@pytest.fixture
def default_hydro_properties() -> HydroProperties:
    return HydroProperties(
        inter_daily_breakdown=1,
        intra_daily_modulation=24,
        inter_monthly_breakdown=1,
        reservoir=False,
        reservoir_capacity=0,
        follow_load=True,
        use_water=False,
        hard_bounds=False,
        initialize_reservoir_date=0,
        use_heuristic=True,
        power_to_level=False,
        use_leeway=False,
        leeway_low=1,
        leeway_up=1,
        pumping_efficiency=1,
    )


@pytest.fixture
def actual_hydro_ini(local_study_with_hydro) -> IniFile:
    return IniFile(
        local_study_with_hydro.service.config.study_path, IniFileTypes.HYDRO_INI
    )


@pytest.fixture
def area_fr(local_study_with_hydro) -> Area:
    return local_study_with_hydro.get_areas()["fr"]


@pytest.fixture
def fr_solar(area_fr) -> None:
    return area_fr.create_solar(pd.DataFrame())


@pytest.fixture
def fr_wind(area_fr) -> None:
    return area_fr.create_wind(pd.DataFrame())


@pytest.fixture
def fr_load(area_fr) -> None:
    return area_fr.create_load(pd.DataFrame())


@pytest.fixture
def local_study_with_constraint(local_study_with_hydro) -> Study:
    local_study_with_hydro.create_binding_constraint(name="test constraint")
    return local_study_with_hydro


@pytest.fixture
def test_constraint(local_study_with_constraint) -> BindingConstraint:
    return local_study_with_constraint.get_binding_constraints()["test constraint"]


@pytest.fixture
def default_constraint_properties() -> BindingConstraintProperties:
    return BindingConstraintProperties(
        enabled=True,
        time_step=BindingConstraintFrequency.HOURLY,
        operator=BindingConstraintOperator.LESS,
        comments="",
        filter_year_by_year="hourly",
        filter_synthesis="hourly",
        group="default",
    )
