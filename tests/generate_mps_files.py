import subprocess
from configparser import ConfigParser
import ortools.linear_solver.pywraplp as pywraplp
from ortools.linear_solver.python import model_builder
import re
import pandas as pd


def generate_mps_file(study_path: str, antares_path: str) -> str:
    name_solver = antares_path.split("/")[-1]
    assert "solver" in name_solver
    # assert float(name_solver.split("-")[1]) >= 8.6
    res = subprocess.run(
        [
            antares_path,
            "--named-mps-problems",
            "--name=export_mps",
            "--expansion",  # à enlever au besoin
            study_path,
        ],
        capture_output=True,
        text=True,
    )
    output = res.stdout.split("\n")
    idx_line = [l for l in output if " Output folder : " in l]
    assert len(idx_line) >= 1
    output_folder = idx_line[0].split(" Output folder : ")[1]
    output_folder = output_folder.replace("\\", "/")
    return output_folder


def read_mps(path, name_scenario, week, name_solver):
    mps_path = path + f"/problem-{name_scenario}-{week+1}--optim-nb-1.mps"
    model = model_builder.ModelBuilder()  # type: ignore[no-untyped-call]
    model.import_from_mps_file(mps_path)
    model_proto = model.export_to_proto()

    solver = pywraplp.Solver.CreateSolver(name_solver)
    assert solver, "Couldn't find any supported solver"
    solver.EnableOutput()

    solver.LoadModelFromProtoWithUniqueNamesOrDie(model_proto)

    return solver


def delete_variable(model, hours_in_week: int, name_variable: str) -> None:
    var = model.variables()
    var_id = [i for i in range(len(var)) if re.search(name_variable, var[i].name())]
    assert len(var_id) in [0, hours_in_week]
    if len(var_id) == hours_in_week:
        for i in var_id:
            var[i].SetLb(-model.Infinity())
            var[i].SetUb(model.Infinity())
            model.Objective().SetCoefficient(var[i], 0)


def delete_constraint(model, hours_in_week: int, name_constraint: str) -> None:
    cons = model.constraints()
    cons_id = [
        i for i in range(len(cons)) if re.search(name_constraint, cons[i].name())
    ]
    assert len(cons_id) in [0, hours_in_week]
    if len(cons_id) == hours_in_week:
        for i in cons_id:
            cons[i].Clear()
            cons[i].SetBounds(lb=0, ub=0)


def solve_complete_problem(solver):
    parameters = pywraplp.MPSolverParameters()

    # Paramètres à utiliser avec Xpress
    solver.SetSolverSpecificParametersAsString("THREADS 1")
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)
    parameters.SetDoubleParam(parameters.DUAL_TOLERANCE, 1e-7)
    parameters.SetDoubleParam(parameters.PRIMAL_TOLERANCE, 1e-7)

    solver.Solve(parameters)


def inspect_variables(solver):
    vars = solver.variables()
    df_vars = pd.DataFrame([vars[i] for i in range(len(vars))], columns=["var"])
    df_vars["names"] = df_vars["var"].apply(lambda x: x.name())
    df_vars["split"] = df_vars["names"].apply(lambda x: x.strip().split("::"))
    df_vars["name_var"] = df_vars["split"].apply(lambda x: x[0])
    df_vars["antares_object"] = df_vars["split"].apply(lambda x: x[1].split("<")[0])
    df_vars["name_antares_object"] = df_vars["split"].apply(
        lambda x: x[1].split("<")[1].split(">")[0]
    )
    df_vars["subobject"] = df_vars["split"].apply(
        lambda x: x[2] if len(x) >= 4 else "None"
    )
    df_vars["time"] = df_vars["split"].apply(
        lambda x: int(x[-1].split("<")[1].split(">")[0])
    )

    return df_vars


def find_thermal_var(solver,variable):

    var = solver.variables()
    var_id = [
        i for i in range(len(var)) if re.search(variable, var[i].name())
    ]

    df_vars = pd.DataFrame([var[i] for i in var_id], columns=["var"])
    df_vars["names"] = df_vars["var"].apply(lambda x: x.name())
    df_vars["split"] = df_vars["names"].apply(lambda x: x.strip().split("::"))
    # df_vars["name_var"] = df_vars["split"].apply(lambda x: x[0])
    # df_vars["type_antares_object"] = df_vars["split"].apply(
    #     lambda x: x[1].split("<")[0]
    # )
    df_vars["name_antares_object"] = df_vars["split"].apply(
        lambda x: x[1].split("<")[1].split(">")[0]
    )
    df_vars["subobject"] = df_vars["split"].apply(
        lambda x: x[2] if len(x) >= 4 else "None"
    )
    df_vars["cluster_name"] = (
        df_vars["name_antares_object"]
        + "_"
        + df_vars["subobject"].apply(lambda x: x.split("<")[1].split(">")[0])
    )

    df_vars["reserve_name"] = df_vars["split"].apply(
        lambda x: x[3].split("<")[1].split(">")[0]
    )

    df_vars["time"] = df_vars["split"].apply(
        lambda x: int(x[-1].split("<")[1].split(">")[0])
    )

    df_vars["id_var"] = var_id

    df_vars["lb"] = [var[i].lb() for i in var_id]
    df_vars["ub"] = [var[i].ub() for i in var_id]

    df_vars = df_vars.assign(sol=[var[i].solution_value() for i in var_id])

    return df_vars


def change_lower_bound(solver, var_id: int, lb: float):
    var = solver.variables()
    var[var_id].SetLb(lb)

def change_upper_bound(solver, var_id: int, ub: float):
    var = solver.variables()
    var[var_id].SetUb(ub)


def get_ini_file(dir_study: str) -> ConfigParser:
    ini_file = ConfigParser()
    ini_file.read(dir_study)

    return ini_file


def milp_version(model):
    vars = model.variables()
    interger_vars = [
        i
        for i in range(len(vars))
        if vars[i].name().strip().split("::")[0]
        in [
            "NODU",
            "NumberBreakingDownDispatchableUnits",
            "NumberStartingDispatchableUnits",
            "NumberStoppingDispatchableUnits",
        ]
    ]
    for i in interger_vars:
        vars[i].SetInteger()
