from pathlib import Path

import yaml
from antares.craft.model.area import Area
from pydantic import BaseModel

from andromede.study.parsing import InputComponent, InputComponentParameter


def resolve_path(path_str: Path) -> Path:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError

    absolute_path = path.resolve()
    return absolute_path


def transform_to_yaml(model: BaseModel, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as yaml_file:
        yaml.dump(
            {"study": model.model_dump(by_alias=True, exclude_unset=True)},
            yaml_file,
            allow_unicode=True,
        )


def convert_hydro_to_component_list(area: Area) -> list[InputComponent]:
    raise NotImplementedError


# def convert_st_storages_to_component_list(area: Area) -> list[InputComponent]:
#     raise NotImplementedError




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

