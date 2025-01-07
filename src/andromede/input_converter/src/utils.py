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
    components = []
    for area in areas:
        components.append(
            InputComponent(
                id=area.id,
                model="area",
                parameters=[
                    InputComponentParameter(
                        name="energy_cost_unsupplied",
                        type="constant",
                        value=area.properties.energy_cost_unsupplied,
                    ),
                    InputComponentParameter(
                        name="energy_cost_spilled",
                        type="constant",
                        value=area.properties.energy_cost_spilled,
                    ),
                ],
            )
        )
    return components


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


def convert_thermals_to_component_list(
    areas: list[Area], root_path: Path
) -> list[InputComponent]:
    components = []
    # Ajouter les composants des thermals pour chaque area
    for area in areas:
        thermals = area.read_thermal_clusters()
        for thermal in thermals:
            series_path = (
                root_path
                / "input"
                / "thermal"
                / "series"
                / Path(area.id)
                / Path(thermal.name)
                / "series.txt"
            )
            prepro_data_path = (
                root_path
                / "input"
                / "thermal"
                / "prepro"
                / Path(area.id)
                / Path(thermal.name)
                / "data.txt"
            )
            prepro_modulation_path = (
                root_path
                / "input"
                / "thermal"
                / "prepro"
                / Path(area.id)
                / Path(thermal.name)
                / "modulation.txt"
            )
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
                                name=f"{thermal.id}_series",
                                type="timeseries",
                                timeseries=str(series_path),
                            ),
                            InputComponentParameter(
                                name=f"{thermal.id}_prepro_data",
                                type="timeseries",
                                timeseries=str(prepro_data_path),
                            ),
                            InputComponentParameter(
                                name=f"{thermal.id}_prepro_modulation",
                                type="timeseries",
                                timeseries=str(prepro_modulation_path),
                            ),
                        ],
                    )
                    for thermal in thermals
                ]
            )
    return components
