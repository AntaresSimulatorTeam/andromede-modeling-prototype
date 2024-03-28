from pathlib import Path

from andromede.model.parsing import parse_yaml_components


def test_parsing_components_ok(data_dir: Path):
    compo_file = data_dir / "components.yml"

    with compo_file.open() as c:
        input_compo = parse_yaml_components(c)
    assert input_compo.id == "components"
    assert len(input_compo.components) == 2
