from pathlib import Path

import pytest

from andromede.model.parsing import (
    components_model_consistency,
    parse_yaml_components,
    parse_yaml_library,
)


class MockInputModel:
    pass


class MockInputComponents:
    def __init__(self, models):
        self.models = models


def test_valid_components(data_dir: Path):
    # Set up mock library and components
    lib_file = data_dir / "lib.yml"
    compo_file = data_dir / "components.yml"

    with lib_file.open() as f:
        input_lib = parse_yaml_library(f)

    with compo_file.open() as c:
        input_compo = parse_yaml_components(c)
    # library, components = components_model_consistency(input_lib, input_compo)


def test_invalid_components():
    # Set up mock library and components
    library_models = ["model1", "model2"]
    component_models = ["model1", "model3"]  # model3 is not defined in library
    mock_library = MockInputModel()
    mock_library.models = library_models
    mock_components = MockInputComponents(component_models)

    # Call the function under test - should raise ValueError
    with pytest.raises(ValueError) as e:
        library, components = components_model_consistency(
            mock_library, mock_components
        )

    # Assert that the correct exception was raised
    assert "Components use undefined models" in str(e.value)
