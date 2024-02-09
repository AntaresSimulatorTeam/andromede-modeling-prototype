import pytest

from andromede.study import TimeScenarioIndex, TimeScenarioSeriesData
from andromede.utils import get_or_add


def test_get_or_add_should_evaluate_lazily() -> None:
    d = {"key1": "value1"}

    def raise_factory() -> None:
        raise AssertionError("No value should be created")

    assert get_or_add(d, "key1", raise_factory) == "value1"
    with pytest.raises(AssertionError, match="No value should be created"):
        get_or_add(d, "key2", raise_factory)

    def value_factory() -> str:
        return "value2"

    assert get_or_add(d, "key2", value_factory) == "value2"


def generate_data(value: float, horizon: int, scenarios: int) -> TimeScenarioSeriesData:
    data = {}
    for absolute_timestep in range(horizon):
        for scenario in range(scenarios):
            data[TimeScenarioIndex(absolute_timestep, scenario)] = value
    return TimeScenarioSeriesData(time_scenario_series=data)
