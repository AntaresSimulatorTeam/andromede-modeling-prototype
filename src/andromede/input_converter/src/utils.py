from pathlib import Path
from antares.model.area import Area
from andromede.study.parsing import (
    InputComponent,
    InputComponents,
    InputComponentParameter,
)
from pydantic import BaseModel


def resolve_path(path_str):
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError

    absolute_path = path.resolve()
    return absolute_path


def convert_area_to_components(areas: list[Area]) -> BaseModel:
    return InputComponents(
        nodes=[InputComponent(id=area.id, model="area") for area in areas],
        components=[],
        connections=[],
    )


def convert_renewable_to_components(area: Area) -> list:
    renewables = area.read_renewables()
    return [
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
                    type="timeserie",
                    timeseries=str(renewable.get_timeseries()),
                ),
            ],
        )
        for renewable in renewables
    ]


def convert_hydro_to_components(area: Area) -> list:
    raise NotImplementedError


def convert_st_storages_to_components(area: Area) -> list:
    raise NotImplementedError


def convert_thermals_to_components(area: Area) -> list:
    raise NotImplementedError


def convert_load_matrix_to_components(area: Area) -> list:
    raise NotImplementedError


def convert_misc_gen_to_components(area: Area) -> list:
    raise NotImplementedError


def convert_reserves_matrix_to_components(area: Area) -> list:
    raise NotImplementedError


def convert_wind_matrix_to_components(area: Area) -> list:
    raise NotImplementedError


def convert_solar_matrix_to_components(area: Area) -> list:
    raise NotImplementedError
