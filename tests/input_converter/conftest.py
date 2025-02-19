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
from antares.craft.model.renewable import (
    RenewableClusterProperties,
)
from antares.craft.model.study import Study, create_study_local
from antares.craft.tools.ini_tool import IniFile, InitializationFilesTypes


@pytest.fixture
def local_study(tmp_path) -> Study:
    """
    Create an empty study
    """
    study_name = "studyTest"
    study_version = "880"
    return create_study_local(study_name, study_version, str(tmp_path.absolute()))


@pytest.fixture
def create_csv_from_constant_value():
    def _create_csv_from_constant_value(
        path, filename: str, lines: int, columns: int = 1, value: int = 1
    ) -> None:
        path = path / filename

        # Generate the data
        data = {f"col_{i+1}": [value] * lines for i in range(columns)}
        df = pd.DataFrame(data)

        # Write the data to a file
        df.to_csv(
            path.with_suffix(".txt"),
            sep="\t",
            index=False,
            header=False,
            encoding="utf-8",
        )

    return _create_csv_from_constant_value


@pytest.fixture
def local_study_w_areas(local_study) -> Study:
    """
    Create an empty study
    Create 2 areas with custom area properties
    """
    areas_to_create = ["fr", "it"]
    for area in areas_to_create:
        area_properties = AreaPropertiesLocal(
            energy_cost_spilled="1", energy_cost_unsupplied="0.5"
        )
        local_study.create_area(area, properties=area_properties)
    return local_study


@pytest.fixture
def local_study_w_links(local_study_w_areas):
    """
    Create an empty study
    Create 2 areas with custom area properties
    Create another area and 3 links
    """
    local_study_w_areas.create_area("at")
    links_to_create = ["fr_at", "at_it", "fr_it"]
    for link in links_to_create:
        area_from, area_to = link.split("_")
        local_study_w_areas.create_link(area_from=area_from, area_to=area_to)

    return local_study_w_areas


@pytest.fixture
def local_study_w_thermal(local_study_w_links) -> Study:
    """
    Create an empty study
    Create 2 areas with custom area properties
    Create another area and 3 links
    Create a thermal cluster
    """
    thermal_name = "gaz"
    local_study_w_links.get_areas()["fr"].create_thermal_cluster(thermal_name)
    return local_study_w_links


@pytest.fixture
def local_study_with_renewable(local_study_w_thermal) -> Study:
    """
    Create an empty study
    Create 2 areas with custom area properties
    Create another area and 3 links
    Create a thermal cluster
    Create a renewable cluster
    """
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
def actual_renewable_list_ini(local_study_with_renewable) -> IniFile:
    """
    return Ini file from the fixture local_study_with_renewable
    """
    return IniFile(
        local_study_with_renewable.service.config.study_path,
        InitializationFilesTypes.RENEWABLES_LIST_INI,
        area_id="fr",
    )


@pytest.fixture
def local_study_with_st_storage(local_study_with_renewable) -> Study:
    """
    Create an empty study
    Create 2 areas with custom area properties
    Create another area and 3 links
    Create a thermal cluster
    Create a renewable cluster
    Create a short term storage
    """
    storage_name = "short term storage"
    local_study_with_renewable.get_areas()["fr"].create_st_storage(storage_name)
    return local_study_with_renewable


@pytest.fixture
def local_study_with_hydro(local_study_with_st_storage) -> Study:
    """
    Create an empty study
    Create 2 areas with custom area properties
    Create another area and 3 links
    Create a thermal cluster
    Create a renewable cluster
    Create a short term storage
    Create an hydro cluster
    """
    local_study_with_st_storage.get_areas()["fr"].create_hydro()
    return local_study_with_st_storage


@pytest.fixture
def area_fr(local_study_with_hydro) -> Area:
    """
    return area object from the fixture local_study_with_hydro
    """
    return local_study_with_hydro.get_areas()["fr"]


@pytest.fixture
def fr_solar(area_fr) -> None:
    """
    return area object from the fixture local_study_with_hydro
    """
    return area_fr.create_solar(pd.DataFrame([1, 1, 1]))


@pytest.fixture
def fr_wind(area_fr, request) -> None:
    """
    return area object with a wind object that has custom parameters
    """
    command = request.param if hasattr(request, "param") else [1, 1, 1]
    data = pd.DataFrame(command)
    return area_fr.create_wind(data)


@pytest.fixture
def fr_load(area_fr) -> None:
    """
    return area object with a load object that has custom parameters
    """
    return area_fr.create_load(pd.DataFrame([1, 1, 1]))
