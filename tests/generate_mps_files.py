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
    # solver.EnableOutput()
    
    solver.LoadModelFromProtoWithUniqueNamesOrDie(model_proto)

    return solver


def delete_variable(var,model, hours_in_week: int, name_variable: str) -> None:
    var_id = [i for i in range(len(var)) if name_variable in var[i].name()]
    assert len(var_id) in [0, hours_in_week]
    if len(var_id) == hours_in_week:
        for i in var_id:
            var[i].SetLb(-model.Infinity())
            var[i].SetUb(model.Infinity())
            model.Objective().SetCoefficient(var[i], 0)


def delete_constraint(cons, hours_in_week: int, name_constraint: str) -> None:
    cons_id = [
        i for i in range(len(cons)) if name_constraint in cons[i].name()
    ]
    # assert len(cons_id) in [0, hours_in_week]
    # if len(cons_id) == hours_in_week:
    for i in cons_id:
        cons[i].Clear()
        cons[i].SetBounds(lb=0, ub=0)


def solve_complete_problem(solver):
    parameters = pywraplp.MPSolverParameters()

    # Paramètres à utiliser avec Xpress
    solver.SetSolverSpecificParametersAsString("THREADS 1")
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_ON)
    parameters.SetIntegerParam(parameters.SCALING, 0)
    parameters.SetDoubleParam(parameters.DUAL_TOLERANCE, 1e-7)
    parameters.SetDoubleParam(parameters.PRIMAL_TOLERANCE, 1e-7)
    parameters.SetDoubleParam(parameters.RELATIVE_MIP_GAP, 0.0001)

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


def find_var(var,variables):

    ensemble_var = {}
    for variable in variables:
        ensemble_var[variable] = []
    
    for i in range(len(var)):
        var_name = var[i].name()
        for variable in variables:
            if variable in var_name:
                ensemble_var[variable].append(i)

    df_vars = [ 0 ] * len(variables)
    for (j,variable) in enumerate(variables):
        var_id = ensemble_var[variable]

        df_vars[j] = pd.DataFrame([var[i] for i in var_id], columns=["var"])
        df_vars[j]["names"] = df_vars[j]["var"].apply(lambda x: x.name())
        df_vars[j]["split"] = df_vars[j]["names"].apply(lambda x: x.strip().split("::"))
        # df_vars["name_var"] = df_vars["split"].apply(lambda x: x[0])
        # df_vars["type_antares_object"] = df_vars["split"].apply(
        #     lambda x: x[1].split("<")[0]
        # )
        df_vars[j]["name_antares_object"] = df_vars[j]["split"].apply(
            lambda x: x[1].split("<")[1].split(">")[0]
        )
        df_vars[j]["subobject"] = df_vars[j]["split"].apply(
            lambda x: x[2] if len(x) >= 4 else "None"
        )
        df_vars[j]["cluster_name"] = (
            df_vars[j]["name_antares_object"]
            + "_"
            + df_vars[j]["subobject"].apply(lambda x: x.split("<")[1].split(">")[0])
        )

        df_vars[j]["reserve_name"] = df_vars[j]["split"].apply(
            lambda x: x[3].split("<")[1].split(">")[0]
        )

        # df_vars["time"] = df_vars["split"].apply(
        #     lambda x: int(x[-1].split("<")[1].split(">")[0])
        # )

        df_vars[j]["id_var"] = var_id

        df_vars[j]["lb"] = [var[i].lb() for i in var_id]
        df_vars[j]["ub"] = [var[i].ub() for i in var_id]

        df_vars[j] = df_vars[j].assign(sol=[var[i].solution_value() for i in var_id])

    return df_vars


def change_lower_bound(var, var_id: int, lb: float):
    var[var_id].SetLb(lb)

def change_upper_bound(var, var_id: int, ub: float):
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
        vars[i].SetInteger(True)

def get_basis(solver:pywraplp.Solver) -> tuple[list, list]:
    var_basis = []
    con_basis = []
    for var in solver.variables():
        var_basis.append(var.basis_status())
    for con in solver.constraints():
        con_basis.append(con.basis_status())
    return var_basis, con_basis
 
def load_basis(solver:pywraplp.Solver, basis) -> None:
    len_cons = len(solver.constraints())
    len_vars = len(solver.variables())
    solver.SetStartingLpBasis(
        basis[0][:len_vars], basis[1][:len_cons]
    )