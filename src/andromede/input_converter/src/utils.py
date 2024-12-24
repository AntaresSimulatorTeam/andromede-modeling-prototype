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


def convert_renewable_to_component_list(
    areas: list[Area], root_path: Path
) -> list[InputComponent]:
    components = []
    for area in areas:
        renewables = area.read_renewables()
        for renewable in renewables:
            series_path = (
                root_path
                / "input"
                / "renewables"
                / "series"
                / Path(area.id)
                / Path(renewable.id)
                / "series.txt"
            )
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
                                timeseries=str(series_path),
                            ),
                        ],
                    )
                    for renewable in renewables
                ]
            )

    return components


def convert_hydro_to_component_list(area: Area) -> list[InputComponent]:
    raise NotImplementedError

