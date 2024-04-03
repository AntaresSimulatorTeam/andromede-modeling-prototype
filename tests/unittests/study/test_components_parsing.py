from pathlib import Path

from andromede.study.parsing import parse_yaml_components
from andromede.study.resolve_components import resolve_components_and_cnx


def test_parsing_components_ok(data_dir: Path):
    compo_file = data_dir / "components.yml"

    with compo_file.open() as c:
        input_compo = parse_yaml_components(c)
    assert len(input_compo.components) == 2
    assert len(input_compo.nodes) == 1
    assert len(input_compo.connections) == 2

    result = resolve_components_and_cnx(input_compo)

    assert len(result.components) == 3
    assert len(result.connections) == 2
