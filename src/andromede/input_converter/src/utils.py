from pathlib import Path

from antares.craft.model.area import Area
from pydantic import BaseModel

from andromede.study.parsing import (
    InputComponent,
    InputComponentParameter,
    InputComponents,
)


def resolve_path(path_str: Path) -> Path:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError

    absolute_path = path.resolve()
    return absolute_path


def convert_area_to_component_list(areas: list[Area]) -> list[InputComponent]:
    return [InputComponent(id=area.id, model="area") for area in areas]


def convert_renewable_to_components(area: Area) -> list[InputComponent]:
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
                    type="timeseries",
                    timeseries=str(renewable.get_timeseries()),
                ),
            ],
        )
        for renewable in renewables
    ]


def convert_hydro_to_components(area: Area) -> list[InputComponent]:
    raise NotImplementedError


def convert_st_storages_to_components(area: Area) -> list[InputComponent]:
    raise NotImplementedError


def convert_thermals_to_components(area: Area) -> list[InputComponent]:
    raise NotImplementedError


def convert_load_matrix_to_components(area: Area) -> list[InputComponent]:
    raise NotImplementedError


def convert_misc_gen_to_components(area: Area) -> list[InputComponent]:
    raise NotImplementedError


def convert_reserves_matrix_to_components(area: Area) -> list[InputComponent]:
    raise NotImplementedError


def convert_wind_matrix_to_components(area: Area) -> list[InputComponent]:
    raise NotImplementedError


def convert_solar_matrix_to_components(area: Area) -> list[InputComponent]:
    raise NotImplementedError
