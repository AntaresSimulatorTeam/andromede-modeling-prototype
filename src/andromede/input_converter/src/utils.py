from pathlib import Path

from antares.craft.model.area import Area
from pydantic import BaseModel

from andromede.study.parsing import (
    InputComponent,
    InputComponentParameter,
)


def resolve_path(path_str: Path) -> Path:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError

    absolute_path = path.resolve()
    return absolute_path


def convert_area_to_component_list(areas: list[Area]) -> list[InputComponent]:
    return [InputComponent(id=area.id, model="area") for area in areas]


def convert_renewable_to_component_list(areas: list[Area]) -> list[InputComponent]:
    components = []
    components.extend([InputComponent(id=area.id, model="area") for area in areas])

    for area in areas:
        renewables = area.read_renewables()
        components.extend(
            [
                InputComponent(
                    id=renewable.id,
                    model="renewable",
                    parameters=[
                        InputComponentParameter(
                            name="unit_count",
                            type="constant",
                            value=renewable.properties.unit_count,
                        ),
                        InputComponentParameter(
                            name="nominal_capacity",
                            type="constant",
                            value=renewable.properties.nominal_capacity,
                        ),
                        InputComponentParameter(
                            name=renewable.id,
                            type="timeseries",
                            timeseries=str(renewable.get_timeseries()),
                        ),
                    ],
                )
                for renewable in renewables
            ]
        )

    return components


def convert_hydro_to_component_list(area: Area) -> list[InputComponent]:
    raise NotImplementedError


# def convert_st_storages_to_component_list(area: Area) -> list[InputComponent]:
#     raise NotImplementedError


def convert_thermals_to_component_list(
    areas: list[Area], root_path: Path
) -> list[InputComponent]:
    components = []

    # Ajouter les composants des areas
    components.extend([InputComponent(id=area.id, model="area") for area in areas])

    # Ajouter les composants des thermals pour chaque area
    for area in areas:
        thermals = area.read_thermal_clusters()
        components.extend(
            [
                InputComponent(
                    id=thermal.id,
                    model="thermal",
                    parameters=[
                        InputComponentParameter(
                            name="unit_count",
                            type="constant",
                            value=thermal.properties.unit_count,
                        ),
                        InputComponentParameter(
                            name="efficiency",
                            type="constant",
                            value=thermal.properties.efficiency,
                        ),
                        InputComponentParameter(
                            name="nominal_capacity",
                            type="constant",
                            value=thermal.properties.nominal_capacity,
                        ),
                        InputComponentParameter(
                            name=f"{thermal.id}_prepro_data",
                            type="timeseries",
                            timeseries=str(thermal.get_prepro_data_matrix()),
                        ),
                        InputComponentParameter(
                            name=f"{thermal.id}_prepro_modulation",
                            type="timeseries",
                            timeseries=str(thermal.get_prepro_modulation_matrix()),
                        ),
                        InputComponentParameter(
                            name=f"{thermal.id}_series",
                            type="timeseries",
                            timeseries=str(thermal.get_series_matrix()),
                        ),
                        InputComponentParameter(
                            name=f"{thermal.id}_co2_cost",
                            type="timeseries",
                            timeseries=str(thermal.get_co2_cost_matrix()),
                        ),
                        InputComponentParameter(
                            name=f"{thermal.id}_fuel_cost",
                            type="timeseries",
                            timeseries=str(thermal.get_fuel_cost_matrix()),
                        ),
                    ],
                )
                for thermal in thermals
            ]
        )

    return components


def convert_load_matrix_to_component_list(
    areas: list[Area], root_path: Path
) -> list[InputComponent]:
    components = []
    for area in areas:
        timeserie = root_path / "input" / "load" / "series" / f"load_{root_path}"
        components.extend(
            [
                InputComponent(
                    id=area.id,
                    model="load",
                    parameters=[
                        InputComponentParameter(
                            name=f"{area.id}_load",
                            type="timeseries",
                            timeseries=str(timeserie),
                        )
                    ],
                )
            ]
        )

    return components


def convert_misc_gen_to_component_list(
    areas: list[Area], root_path: Path
) -> list[InputComponent]:
    components = []

    for area in areas:
        components.extend(
            [
                InputComponent(
                    id=area.id,
                    model="misc_gen",
                    parameters=[
                        InputComponentParameter(
                            name=f"{area.id}_misc_gen",
                            type="timeseries",
                            timeseries=str(area.get_misc_gen_matrix()),
                        )
                    ],
                )
            ]
        )

    return components


def convert_reserves_matrix_to_component_list(
    areas: list[Area], root_path: Path
) -> list[InputComponent]:
    components = []

    for area in areas:
        components.extend(
            [
                InputComponent(
                    id=area.id,
                    model="reserves",
                    parameters=[
                        InputComponentParameter(
                            name=f"{area.id}_reserves",
                            type="timeseries",
                            timeseries=str(area.get_reserves_matrix()),
                        )
                    ],
                )
            ]
        )

    return components


def convert_wind_matrix_to_component_list(
    areas: list[Area], root_path: Path
) -> list[InputComponent]:
    components = []

    for area in areas:
        components.extend(
            [
                InputComponent(
                    id=area.id,
                    model="wind",
                    parameters=[
                        InputComponentParameter(
                            name=f"{area.id}_wind",
                            type="timeseries",
                            timeseries=str(area.get_wind_matrix()),
                        )
                    ],
                )
            ]
        )

    return components


def convert_solar_matrix_to_component_list(
    areas: list[Area], root_path: Path
) -> list[InputComponent]:
    components = []

    for area in areas:
        components.extend(
            [
                InputComponent(
                    id=area.id,
                    model="solar",
                    parameters=[
                        InputComponentParameter(
                            name=f"{area.id}_solar",
                            type="timeseries",
                            timeseries=str(area.get_solar_matrix()),
                        )
                    ],
                )
            ]
        )

    return components
