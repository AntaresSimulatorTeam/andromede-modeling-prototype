from andromede.simulation.output_values import OutputValues
from andromede.study.data import TimeIndex, TimeScenarioIndex
from tests.unittests.study.test_components_parsing import *
from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.study.resolve_components import resolve_system

import pandas as pd

@pytest.mark.parametrize(
    "system_file, optim_result_file, timespan, batch",
    [
        ("dsr_validation.yml","dsr_case_results.csv",168,20),     
        ("base_validation.yml","base_case_results.csv",168,20),
        ("electrolyser_validation.yml","electrolyser_case_results.csv",168,20),
        ("storage_validation.yml","storage_case_results.csv",168,20),
        ("bde_system.yml","bde_case_results.csv",168,20)
    ] )

def test_model_behaviour(
    system_file: str,
    optim_result_file:str,
    timespan: int,
    batch: int
) -> None:
    scenarios = 1
    syspath ="tests/data/systems/"
    tspath = "tests/data/series/"
    respath = "tests/data/results/"
    libpaths = ["src/andromede/libs/antares_historic/antares_historic.yml","src/andromede/libs/reference_models/andromede_v1_models.yml"]
    compo_file = open(syspath+system_file)
    input_libraries = [parse_yaml_library(open(libfile)) for libfile in libpaths]
    input_component = parse_yaml_components(compo_file)
    result_lib = resolve_library(input_libraries)
    components_input = resolve_system(input_component, result_lib)
    database = build_data_base(input_component, Path(tspath))
    network = build_network(components_input)
    reference_values = (pd.read_csv(respath+optim_result_file,header=None)).values
    for k in range(batch):
        problem = build_problem(network, database, TimeBlock(1, [i for i in range(k*timespan,(k+1)*timespan)]), scenarios)
        status = problem.solver.Solve()
        assert status == problem.solver.OPTIMAL
        assert(1e-6>abs(reference_values[k,0]-problem.solver.Objective().Value())/reference_values[k,0])