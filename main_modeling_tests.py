from tests.functional.test_andromede_yml import *
from tests.unittests.study.test_components_parsing import *
from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library
import pandas as pd


#Macro-parameters
dbpath = Path('tests/test_full_modeler/')
libpath = "src/andromede/libs/antares_historic/antares_historic_temp.yml"
scenarios = 1


def main_base_case(timespan):
    #End to end test for the base_case study
    compo_file = open("tests/test_full_modeler/base_case.yml")
    libfile = open(libpath)
    input_library = parse_yaml_library(libfile)
    input_component = parse_yaml_components(compo_file)
    result_lib = resolve_library([input_library])
    components_input = resolve_components_and_cnx(input_component, result_lib)
    consistency_check(components_input.components, result_lib.models)
    database = build_data_base(input_component, dbpath)
    network = build_network(components_input)
    problem = build_problem(network, database, TimeBlock(1, [i for i in range(0,timespan)]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    print(problem.solver.Objective().Value())
    results = (OutputValues(problem))
    print(results)
    dataframe = pd.DataFrame()
    for cluster in ["gas_base_zone","coal_base_zone","oil_base_zone"]:
        var_result = results.component(cluster).var("generation")
        dataframe[cluster] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("base_zone").var("spillage")
    dataframe["spillage"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("base_zone").var("unsupplied_energy")
    dataframe["unsupplied_energy"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    print(dataframe)
    dataframe.to_excel("../parallel_run/base_case_modeler.xlsx")

def main_dsr_case(timespan):
    #End to end test for the base_case study + demand-side response (DSR)
    compo_file = open("tests/test_full_modeler/dsr.yml")
    libfile = open(libpath)
    input_library = parse_yaml_library(libfile)
    input_component = parse_yaml_components(compo_file)
    result_lib = resolve_library([input_library])
    components_input = resolve_components_and_cnx(input_component, result_lib)
    consistency_check(components_input.components, result_lib.models)
    database = build_data_base(input_component, dbpath)
    network = build_network(components_input)
    problem = build_problem(network, database, TimeBlock(1, [i for i in range(0,timespan)]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    print(problem.solver.Objective().Value())
    results = (OutputValues(problem))
    print(results)
    dataframe = pd.DataFrame()
    for cluster in ["gas_base_zone","coal_base_zone","oil_base_zone"]:
        var_result = results.component(cluster).var("generation")
        dataframe[cluster] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("base_zone").var("spillage")
    dataframe["spillage"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("base_zone").var("unsupplied_energy")
    dataframe["unsupplied_energy"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("dsr_base_zone").var("curtailment")
    dataframe["dsr_curtailment"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    print(dataframe)
    dataframe.to_excel("../parallel_run/dsr_case_modeler.xlsx")

def main_electrolyser_case(timespan):
    #End to end test for the base_case study + electrolyser
    compo_file = open("tests/test_full_modeler/electrolyser.yml")
    libfile = open(libpath)
    input_library = parse_yaml_library(libfile)
    input_component = parse_yaml_components(compo_file)
    result_lib = resolve_library([input_library])
    components_input = resolve_components_and_cnx(input_component, result_lib)
    consistency_check(components_input.components, result_lib.models)
    database = build_data_base(input_component, dbpath)
    network = build_network(components_input)
    problem = build_problem(network, database, TimeBlock(1, [i for i in range(0,timespan)]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    print(problem.solver.Objective().Value())
    results = (OutputValues(problem))
    print(results)
    dataframe = pd.DataFrame()
    for cluster in ["gas_base_zone","coal_base_zone","oil_base_zone"]:
        var_result = results.component(cluster).var("generation")
        dataframe[cluster] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("base_zone").var("spillage")
    dataframe["spillage"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("base_zone").var("unsupplied_energy")
    dataframe["unsupplied_energy"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("hydrogen_zone").var("spillage")
    dataframe["hydrogen_zone_spillage"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("hydrogen_zone").var("unsupplied_energy")
    dataframe["hydrogen_zone_unsupplied_energy"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("hydrogen_backup").var("generation")
    dataframe["hydrogen_backup_generation"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("electrolyser").var("power")
    dataframe["electrolyser_power"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    print(dataframe)
    dataframe.to_excel("../parallel_run/electrolyser_case_modeler.xlsx")


def main_storage_case(timespan):
    #End to end test for the base_case study + short-term storage
    compo_file = open("tests/test_full_modeler/storage.yml")
    libfile = open(libpath)
    input_library = parse_yaml_library(libfile)
    input_component = parse_yaml_components(compo_file)
    result_lib = resolve_library([input_library])
    components_input = resolve_components_and_cnx(input_component, result_lib)
    consistency_check(components_input.components, result_lib.models)
    database = build_data_base(input_component, dbpath)
    network = build_network(components_input)
    problem = build_problem(network, database, TimeBlock(1, [i for i in range(0,timespan)]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    print(problem.solver.Objective().Value())
    results = (OutputValues(problem))
    pbfile = problem.export_as_lp()
    print(pbfile)
    print(results)
    dataframe = pd.DataFrame()
    for cluster in ["gas_base_zone","coal_base_zone","oil_base_zone"]:
        var_result = results.component(cluster).var("generation")
        dataframe[cluster] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("base_zone").var("spillage")
    dataframe["spillage"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("base_zone").var("unsupplied_energy")
    dataframe["unsupplied_energy"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("storage_base_zone").var("p_withdrawal")
    dataframe["storage_withdrawal"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("storage_base_zone").var("p_injection")
    dataframe["storage_injection"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    var_result = results.component("storage_base_zone").var("level")
    dataframe["storage_level"] = [var_result._value[TimeScenarioIndex(t, 0)] for t in range(timespan)]
    print(dataframe)
    dataframe.to_excel("../parallel_run/storage_case_modeler.xlsx")


#main_base_case(7*24)
#main_dsr_case(7*24)
#main_electrolyser_case(7*24)
main_storage_case(5)
print("Test terminated")



