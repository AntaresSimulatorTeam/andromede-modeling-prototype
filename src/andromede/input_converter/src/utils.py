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
