from pathlib import Path

from andromede.model.parsing import parse_yaml_components
from andromede.model.resolve_library import resolve_components_and_cnx


def test_parsing_components_ok(data_dir: Path):
    compo_file = data_dir / "components.yml"
    lib = data_dir / "lib.yml"

    with compo_file.open() as c:
        input_compo = parse_yaml_components(c)
    assert len(input_compo.components) == 2

    components = resolve_components_and_cnx(input_compo)
