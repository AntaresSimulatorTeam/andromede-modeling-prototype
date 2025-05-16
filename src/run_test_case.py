import math
from pathlib import Path

import numpy as np
import pandas as pd


from andromede.model.parsing import  parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation.optimization import build_problem
from andromede.simulation.output_values import OutputValues
from andromede.simulation.time_block import TimeBlock
from andromede.study.parsing import parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    resolve_system,
)


class TestCase:
    ### Simple class to load and manage an Andromede study case
    ### The main function is the "simulation" function: build and solve the optimization problem related to a given week and scenario

    def __init__(self, system_folder, data_folder) -> None:

        # Configuration of the test case: reference to the Andromede library and system .yml files
        self.tspath = data_folder
        self.system_file_path = system_folder + "/system.yml"
        self.library_file_path = system_folder + "/library.yml"
        self.areatype, self.clustertype = (
            "muessli-lib.area",
            "muessli-lib.thermal",
        )
         
        (
            self.UNSP_VAR,
            self.THERMAL_GEN_VAR,
            self.SPILL_VAR,
            self.HYDRO_WITHDRAW_VAR,
            self.HYDRO_INJECTION_VAR,
        ) = (
            "unsupplied_energy",
            "generation",
            "spillage",
            "p_withdrawal",
            "p_injection",
        )
        self.timespan = 168  # Number of hours in a week
        self.T, self.week_number, self.scenario_number = 8760, 52, 1000
        self.tolerance_unsp = 1  # Tolerance for loss of load (in MWh)
        # Parsing the file describing the graph of the system (components and connections between components) : "system.yml"
        with open(self.system_file_path) as compo_file:
            self.input_component = parse_yaml_components(compo_file)
        # Parsing the file describing the models of components (mathematical behaviour of the components) : "library.yml"
        with open(self.library_file_path) as lib_file:
            self.input_library = parse_yaml_library(lib_file)
        # Constructing the Andromede library object from parser
        self.result_lib = resolve_library([self.input_library])
        # Constructing the Andromede system object from parser
        self.system = resolve_system(self.input_component, self.result_lib)
        print("Andromede Library and System resolved. Building database... May take 1-2 mins...")
        database = build_data_base(self.input_component, Path(self.tspath))
        print("Database built. Building network...")
        self.network = build_network(self.system)
        print("Network built. Building optimization problem...")
        # Creation of the OR-tools optimization problem from the system
        self.problem = build_problem(
            self.network,
            database,
            TimeBlock(1, [i for i in range(0, self.timespan)]),
            1,
        )
        del database
        print("Problem built.")
        self.__build_local_db()
        print("Local object database built.")

    def __build_local_db(self):
        ### Temporary function. Builds the local database used to update the optimization problem object (self.problem).
        ### Will be useless once the build_problem function's implementation will be optimized to reduce overhead of building problem

        # Building list of clusters and areas
        self.areas = []
        self.clusters = []
        for el in self.input_component.components:
            if el.model == self.areatype:
                self.areas.append(el.id)
            if el.model == self.clustertype:
                self.clusters.append(el.id)
        # Building database of load profiles
        self.local_db_load = {}
        for area in self.areas:
            self.local_db_load[area] = pd.read_csv(
                self.tspath + f"/residual_load_{area}.txt", sep="\t", header=None
            ).values.astype(np.double)
            assert self.local_db_load[area].shape == (self.T, self.scenario_number)

        # Building database of generators availabilities (pmax modulation)
        self.local_db_modulation = {}
        for cluster in self.clusters:
            self.local_db_modulation[cluster] = pd.read_csv(
                self.tspath + f"/modulation_{cluster}.txt", sep="\t", header=None
            ).values.astype(np.double)
            assert self.local_db_modulation[cluster].shape == (
                self.T,
                self.scenario_number,
            )

        # Building database of storage credits
        self.reference_turbining_credits = {}
        credit_db = {}
        for area in self.areas:
            credit_db[area] = pd.read_csv(
                self.tspath + f"/credits_{area}.txt", sep="\t", header=None
            ).values.astype(np.double)
            assert credit_db[area].shape == (self.week_number, self.scenario_number)
        for week_index in range(self.week_number):
            for scenario_index in range(self.scenario_number):
                self.reference_turbining_credits[(week_index, scenario_index)] = {
                    area: credit_db[area][week_index, scenario_index]
                    for area in self.areas
                }

    def eval_ens(self):
        # Returns the Energy Not Served by area (also called "Unsupplied energy") in MWh
        ens = {}
        for area in self.areas:
            ens[area] = sum(
                i for i in self.results.component(area).var(self.UNSP_VAR).value[0]
            )
        return ens

    def eval_spill(self):
        # Returns the Energy Not Evacuated by area (also called "Spillage") in MWh
        spill = {}
        for area in self.areas:
            spill[area] = sum(
                i for i in self.results.component(area).var(self.SPILL_VAR).value[0]
            )
        return spill

    def eval_lold(self):
        # Returns the loss of load duration by zone, in hours
        lold = {}
        for area in self.areas:
            lold[area] = sum(
                1 if i > self.tolerance_unsp else 0
                for i in self.results.component(area).var(self.UNSP_VAR).value[0]
            )
        return lold

    def eval_thermal_prod(self, techno=""):
        # Returns the production from all thermal units from a same technology. If techno is not provided, this sums over all thermal units
        prod = 0
        for cluster in self.clusters:
            if techno in cluster:
                prod += sum(
                    i
                    for i in self.results.component(cluster)
                    .var(self.THERMAL_GEN_VAR)
                    .value[0]
                )
        return prod

    def eval_net_hydro_prod(self):
        # Returns the hydro production
        prod = 0
        for area in self.areas:
            prod += sum(
                i
                for i in self.results.component(f"hydro_{area}")
                .var(self.HYDRO_WITHDRAW_VAR)
                .value[0]
            ) - sum(
                i
                for i in self.results.component(f"hydro_{area}")
                .var(self.HYDRO_INJECTION_VAR)
                .value[0]
            )
        return prod

    def eval_objective(self):
        return self.problem.solver.Objective().Value()

    def get_load(self, area, week_index, scenario_index):
        # Returns the load vector associated to an area, a week and a scenario
        return self.local_db_load[area][
            week_index * self.timespan : (week_index + 1) * self.timespan,
            scenario_index,
        ]

    def get_availability(self, cluster, week_index, scenario_index):
        # Returns the modulation vector associated to a cluster, a week and a scenario
        return self.local_db_modulation[cluster][
            week_index * self.timespan : (week_index + 1) * self.timespan,
            scenario_index,
        ]

    def __update_load(self, week_index, scenario_index):
        for area in self.areas:
            temp = self.get_load(area, week_index, scenario_index)
            for i in range(self.timespan):
                constraint_name = f"{area}_balance_t{i}_s0"
                self.problem.solver.LookupConstraint(constraint_name).SetUb(temp[i])
                self.problem.solver.LookupConstraint(constraint_name).SetLb(temp[i])

    def __update_modulation(self, week_index, scenario_index):
        for cluster in self.clusters:
            temp = self.get_availability(cluster, week_index, scenario_index)
            for i in range(self.timespan):
                constraint_name = f"{cluster}_availability_t{i}_s0"
                self.problem.solver.LookupConstraint(constraint_name).SetCoefficient(
                    self.problem.solver.LookupVariable(f"{cluster}_p_max_cluster"),
                    -temp[i],
                )

    def __update_credits(self, turbining_credits):
        for area in self.areas:
            self.problem.solver.LookupConstraint(
                f"hydro_{area}_net_injection_credit_t0_s0"
            ).SetUb(turbining_credits[area])

    def __update_problem(self, week_index, scenario_index, turbining_credits):
        ### Temporary function. Builds the local database used to update the optimization problem object (self.problem).
        ### Will be useless when the build_problem function's implementation will be optimized to reduce overhead of building problem
        self.__update_load(week_index, scenario_index)
        self.__update_modulation(week_index, scenario_index)
        self.__update_credits(turbining_credits)

    def simulation(
        self,
        week_index,
        scenario_index,
        turbining_credits=None,
        thermal_capacities=None,
        export_opt_file=None,
    ):
        ### Function building and solving the optimization related to a week, a climate scenario, a set of turbining credits for each zone (dict) and a set of installed capacities for each cluster (dict)
        ### Exemple of value for turbining_credits : {'fr':300000, "ch" : 300000, 'de' : 20000}
        if turbining_credits == None:
            turbining_credits = self.reference_turbining_credits[
                (week_index, scenario_index)
            ]
        ### self.__update_problem = Temporary code 
        ### Instead of building a new optimization problem, we update the existing one to reduce the overhead
        ### The future implementation of the function  "build_problem" from andromede.simulation.optimization should be way more efficient: its overhead will be reduced
        ### Hence, the line below could then be replaced by self.problem = build_problem(...) since it will be easier (for data tracability) for to just build the optimization problem from scratch, rather than updating the previous one
        self.__update_problem(week_index, scenario_index, turbining_credits)
        #self.problem = build_problem(...)
        
        ### Setting thermal capacities
        if thermal_capacities != None:
            raise ValueError(
                "Changing the capacity of the thermal generation unit should be implemented."
            )
        
        ### Problem solution ; logging of output
        self.problem.solver.Solve()
        self.results = OutputValues(self.problem)

        ### Optional export of the optimization problem file for debugging purposes
        if export_opt_file == "lp":
            self.__to_lp_file(week_index, scenario_index)
        elif export_opt_file == "mps":
            self.__to_mps_file(week_index, scenario_index)

        ###Consistency check for debugging purposes (energy balance)
        self.__check_consistency(week_index, scenario_index)

        ### We return the system overallcost, the unsupplied energy (MWh) by zone and the loss of load duration (in hour) by zone
        return self.eval_objective(), self.eval_ens(), self.eval_lold()

    def __to_lp_file(self, week_index, scenario_index):
        # Export the optimization problem as LP file
        with open(f"problem_{week_index}_{scenario_index}.lp", "w") as f:
            f.write(self.problem.solver.ExportModelAsLpFormat(False))
            f.close()

    def __to_mps_file(self, week_index, scenario_index):
        # Export the optimization problem as MPS file
        with open(f"problem_{week_index}_{scenario_index}.mps", "w") as f:
            f.write(self.problem.solver.ExportModelAsMpsFormat(False))
            f.close()

    def __check_consistency(self, week_index, scenario_index):
        # Consistency check for debugging purpose: check energy balance. This function should be updated if new type of models from the library.yml file are used
        load = sum(
            [sum(self.get_load(area, week_index, scenario_index)) for area in self.areas]
        )
        empty = ""
        total_thermal_prod = self.eval_thermal_prod(
            empty
        )  # Mean summing the production of all thermal clusters
        net_hydro = self.eval_net_hydro_prod()
        ens_dict = self.eval_ens()
        ens = sum([ens_dict[key] for key in ens_dict])
        spill_dict = self.eval_spill()
        spill = sum([spill_dict[key] for key in spill_dict])
        assert math.isclose(
            spill + load, total_thermal_prod + net_hydro + ens, rel_tol=1e-6
        )


##### Example of use ######
system_folder = "./tests/muessli/case_3_nodes/" #You can keep this path
data_folder = "../muessli_cases/case_3_nodes/timeseries" #This path has to be changed depending on where you saved the timeseries folder.
case = TestCase(system_folder, data_folder)
T,W = 5, 52


for scenario_index in range(T):
    #scenario_index may take values between 0 and 999
    for week_index in range(W):
        #week_index may take values between 0 and 51
        print(
            scenario_index + 1,
            week_index + 1,
            case.simulation(week_index, scenario_index),
        )
        # Examples of functions to get the input data that changes depending on week/scenario, for proxy-learning purpose
        # res_load_fr = case.get_load("fr",week_index,scenario_index)
        # modulation_nuclear_fr = case.get_availability("nuclear_fr",week_index,scenario_index)

