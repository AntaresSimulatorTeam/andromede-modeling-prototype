from math import ceil,floor

from ortools.sat.python import cp_model
from ortools.linear_solver import pywraplp


def heuristique_opti(
    nbr_on_float : float,
    energy_generation : float,
    generation_reserve_up_primary : float,
    generation_reserve_down_primary : float,
    generation_reserve_up_secondary : float,
    generation_reserve_down_secondary : float,
    generation_reserve_up_tertiary1 : float,
    generation_reserve_down_tertiary1 : float,
    generation_reserve_up_tertiary2 : float,
    generation_reserve_down_tertiary2 : float,
    p_max : float,
    p_min : float,
    participation_max_primary_reserve_up : float,
    participation_max_primary_reserve_down : float,
    participation_max_secondary_reserve_up : float,
    participation_max_secondary_reserve_down : float,
    participation_max_tertiary1_reserve_up : float,
    participation_max_tertiary1_reserve_down : float,
    participation_max_tertiary2_reserve_up : float,
    participation_max_tertiary2_reserve_down : float,
    cost : float,
    startup_cost : float,
    fixed_cost : float,
) -> int:
    
    nbr_on = floor(round(nbr_on_float,12))
    nbr_on_classic = ceil(round(nbr_on_float,12))

    # Instantiate a Glop solver, naming it LinearExample.
    solver = pywraplp.Solver.CreateSolver("GLOP")

    UNSP_primary_up_min = max(0,generation_reserve_up_primary-nbr_on*participation_max_primary_reserve_up)  
    UNSP_primary_down_min = max(0,generation_reserve_down_primary-nbr_on*participation_max_primary_reserve_down)
    UNSP_secondary_up_min = max(0,generation_reserve_up_secondary-nbr_on*participation_max_secondary_reserve_up)  
    UNSP_secondary_down_min = max(0,generation_reserve_down_secondary-nbr_on*participation_max_secondary_reserve_down)
    UNSP_tertiary1_up_min = max(0,generation_reserve_up_tertiary1-nbr_on*participation_max_tertiary1_reserve_up)  
    UNSP_tertiary1_down_min = max(0,generation_reserve_down_tertiary1-nbr_on*participation_max_tertiary1_reserve_down)
    UNSP_tertiary2_up_min = max(0,generation_reserve_up_tertiary2-nbr_on*participation_max_tertiary2_reserve_up)  
    UNSP_tertiary2_down_min = max(0,generation_reserve_down_tertiary2-nbr_on*participation_max_tertiary2_reserve_down)

    x = solver.NumVar(0, energy_generation, "x")
    ya = solver.NumVar(UNSP_primary_up_min, generation_reserve_up_primary, "ya") #UNSP_res+
    za = solver.NumVar(UNSP_primary_down_min, generation_reserve_down_primary, "za")    #UNSP_res-
    yb = solver.NumVar(UNSP_secondary_up_min, generation_reserve_up_secondary, "yb") #UNSP_res+
    zb = solver.NumVar(UNSP_secondary_down_min, generation_reserve_down_secondary, "zb")    #UNSP_res-
    yc = solver.NumVar(UNSP_tertiary1_up_min, generation_reserve_up_tertiary1, "yc") #UNSP_res+
    zc = solver.NumVar(UNSP_tertiary1_down_min, generation_reserve_down_tertiary1, "zc")    #UNSP_res-
    yd = solver.NumVar(UNSP_tertiary2_up_min, generation_reserve_up_tertiary2, "yd") #UNSP_res+
    zd = solver.NumVar(UNSP_tertiary2_down_min, generation_reserve_down_tertiary2, "zd")    #UNSP_res-

    generation_reserve_up = generation_reserve_up_primary + generation_reserve_up_secondary + generation_reserve_up_tertiary1 + generation_reserve_up_tertiary2,
    generation_reserve_down = generation_reserve_down_primary + generation_reserve_down_secondary + generation_reserve_down_tertiary1 + generation_reserve_down_tertiary2,

    borne_max = max(0,generation_reserve_up+energy_generation-nbr_on*p_max)
    borne_min = energy_generation - generation_reserve_down - nbr_on*p_min
    
    solver.Add(1 * x + 1 * ya + 1 * yb + 1 * yc + 1 * yd >= borne_max)
    solver.Add(1 * x - 1 * za - 1 * zb - 1 * zc - 1 * zd <= borne_min)


    solver.Minimize(1000 * (ya + yb + yc + yd) + 1000 * (za + zb+ zc + zd) + (100 - cost) * x)

    # Solve the system.
    status = solver.Solve()

    energy_generation_classique = max(nbr_on_classic * p_min + generation_reserve_down,
                                      min(energy_generation,
                                          nbr_on_classic * p_max - generation_reserve_up))
    gain = fixed_cost  + cost * ( energy_generation_classique - energy_generation) - startup_cost
    if solver.Objective().Value() < gain:  
        return nbr_on
    return nbr_on_classic


def heuristique_opti1(
    nbr_on_float : float,
    energy_generation : float,
    generation_reserve_up_primary : float,
    generation_reserve_down_primary : float,
    generation_reserve_up_secondary : float,
    generation_reserve_down_secondary : float,
    generation_reserve_up_tertiary1 : float,
    generation_reserve_down_tertiary1 : float,
    generation_reserve_up_tertiary2 : float,
    generation_reserve_down_tertiary2 : float,
    p_max : float,
    p_min : float,
    participation_max_primary_reserve_up : float,
    participation_max_primary_reserve_down : float,
    participation_max_secondary_reserve_up : float,
    participation_max_secondary_reserve_down : float,
    participation_max_tertiary1_reserve_up : float,
    participation_max_tertiary1_reserve_down : float,
    participation_max_tertiary2_reserve_up : float,
    participation_max_tertiary2_reserve_down : float,
    cost : float,
    startup_cost : float,
    fixed_cost : float,
) -> int:
    
    nbr_on = floor(round(nbr_on_float,12))
    nbr_on_classic = ceil(round(nbr_on_float,12))

    energy_generation = int(energy_generation)
    generation_reserve_up_primary = int(generation_reserve_up_primary)
    generation_reserve_down_primary = int(generation_reserve_down_primary)
    p_max = int(p_max)
    p_min = int(p_min)
    participation_max_primary_reserve_up = int(participation_max_primary_reserve_up)
    participation_max_primary_reserve_down = int(participation_max_primary_reserve_down)
    cost = int(cost)
    startup_cost = int(startup_cost)
    fixed_cost = int(fixed_cost)

    model = cp_model.CpModel()
    UNSP_primary_up_min = max(0,generation_reserve_up_primary-nbr_on*participation_max_primary_reserve_up)  
    UNSP_primary_down_min = max(0,generation_reserve_down_primary-nbr_on*participation_max_primary_reserve_down)
    x = model.new_int_var(0, energy_generation, "x")  #UNSP_prod
    y = model.new_int_var(UNSP_primary_up_min, generation_reserve_up_primary, "y")  #UNSP_res+
    z = model.new_int_var(UNSP_primary_down_min, generation_reserve_down_primary, "z")    #UNSP_res-
    borne_max = max(0,generation_reserve_up_primary+energy_generation-nbr_on*p_max)
    borne_min = energy_generation - generation_reserve_down_primary - nbr_on*p_min
    model.add(1 * x + 1 * y >= borne_max)
    model.add(1 * x - 1 * z <= borne_min)

    model.minimize(1000 * y + 1000 * z + (100 - cost) * x)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    
    energy_generation_classique = max(nbr_on_classic * p_min + generation_reserve_down_primary,
                                      min(energy_generation,
                                          nbr_on_classic * p_max - generation_reserve_up_primary))
    gain = fixed_cost  + cost * ( energy_generation_classique - energy_generation)
    print(solver.value)
    if solver.objective_value < gain:  
        return nbr_on
    return nbr_on_classic


def nouvelle_heuristique(
    nbr_on_float : float,
    energy_generation : float,
    generation_reserve_up_primary : float,
    generation_reserve_down_primary : float,
    generation_reserve_up_secondary : float,
    generation_reserve_down_secondary : float,
    generation_reserve_up_tertiary1 : float,
    generation_reserve_down_tertiary1 : float,
    generation_reserve_up_tertiary2 : float,
    generation_reserve_down_tertiary2 : float,
    p_max : float,
    p_min : float,
    participation_max_primary_reserve_up : float,
    participation_max_primary_reserve_down : float,
    participation_max_secondary_reserve_up : float,
    participation_max_secondary_reserve_down : float,
    participation_max_tertiary1_reserve_up : float,
    participation_max_tertiary1_reserve_down : float,
    participation_max_tertiary2_reserve_up : float,
    participation_max_tertiary2_reserve_down : float,
    cost : float,
    startup_cost : float,
    fixed_cost : float,
) -> int:
    
    nbr_on = floor(round(nbr_on_float,12))
    nbr_on_classic = ceil(round(nbr_on_float,12))
    UNSP_primary_up = max(0,generation_reserve_up_primary-nbr_on*participation_max_primary_reserve_up)
    UNSP_primary_down = max(0,generation_reserve_down_primary-nbr_on*participation_max_primary_reserve_down)
    UNSP_prod = max(0,energy_generation+generation_reserve_up_primary-nbr_on*p_max)-UNSP_primary_up
    cout = 1000*(UNSP_primary_up+UNSP_primary_down)+ (100-cost)*UNSP_prod
    energy_generation_classique = max(nbr_on_classic * p_min + generation_reserve_down_primary,
                                      min(energy_generation,
                                          nbr_on_classic * p_max - generation_reserve_up_primary))
    gain = fixed_cost  + cost * ( energy_generation_classique - energy_generation)
    if cout < gain:
        return(nbr_on)
    return(nbr_on_classic)

def old_heuristique(
    nbr_on_float : float,
    energy_generation : float,
    generation_reserve_up_primary : float,
    generation_reserve_down_primary : float,
    generation_reserve_up_secondary : float,
    generation_reserve_down_secondary : float,
    generation_reserve_up_tertiary1 : float,
    generation_reserve_down_tertiary1 : float,
    generation_reserve_up_tertiary2 : float,
    generation_reserve_down_tertiary2 : float,
    p_max : float,
    p_min : float,
    participation_max_primary_reserve_up : float,
    participation_max_primary_reserve_down : float,
    participation_max_secondary_reserve_up : float,
    participation_max_secondary_reserve_down : float,
    participation_max_tertiary1_reserve_up : float,
    participation_max_tertiary1_reserve_down : float,
    participation_max_tertiary2_reserve_up : float,
    participation_max_tertiary2_reserve_down : float,
    cost : float,
    startup_cost : float,
    fixed_cost : float,
) -> int:
    
    nbr_on = ceil(round(nbr_on_float,12))
    return(nbr_on)