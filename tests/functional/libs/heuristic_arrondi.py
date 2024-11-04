from math import ceil,floor
from typing import Callable, List, Optional

from ortools.linear_solver import pywraplp
import ortools.linear_solver.pywraplp as lp

def arrondi_opti_avec_start_up(
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
    cost_participation_primary_reserve_up : float,
    cost_participation_primary_reserve_down : float,
    cost_participation_secondary_reserve_up : float,
    cost_participation_secondary_reserve_down : float,
    cost_participation_tertiary1_reserve_up : float,
    cost_participation_tertiary1_reserve_down : float,
    cost_participation_tertiary2_reserve_up : float,        
    cost_participation_tertiary2_reserve_down : float,
    spillage_cost : float,
    ens_cost : float,
    primary_reserve_up_not_supplied_cost : float,
    primary_reserve_down_not_supplied_cost : float,
    secondary_reserve_up_not_supplied_cost : float,
    secondary_reserve_down_not_supplied_cost : float,
    tertiary1_reserve_up_not_supplied_cost : float,
    tertiary1_reserve_down_not_supplied_cost : float,
    tertiary2_reserve_up_not_supplied_cost : float,
    tertiary2_reserve_down_not_supplied_cost : float,
) -> int:
    
    nbr_on = floor(round(nbr_on_float,12))
    nbr_on_classic = ceil(round(nbr_on_float,12))

    solver = lp.Solver.CreateSolver("SCIP")
    # pywraplp.Solver.CreateSolver("GLOP")

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

    generation_reserve_up = generation_reserve_up_primary + generation_reserve_up_secondary + generation_reserve_up_tertiary1 + generation_reserve_up_tertiary2
    generation_reserve_down = generation_reserve_down_primary + generation_reserve_down_secondary + generation_reserve_down_tertiary1 + generation_reserve_down_tertiary2

    borne_max = max(0,generation_reserve_up + energy_generation - nbr_on * p_max)
    borne_min = energy_generation - generation_reserve_down - nbr_on*p_min
    
    solver.Add(1 * x + 1 * ya + 1 * yb + 1 * yc + 1 * yd >= borne_max)
    solver.Add(1 * x - 1 * za - 1 * zb - 1 * zc - 1 * zd <= borne_min)


    solver.Minimize((primary_reserve_up_not_supplied_cost-cost_participation_primary_reserve_up) * ya
                     + (secondary_reserve_up_not_supplied_cost-cost_participation_secondary_reserve_up) * yb
                      + (tertiary1_reserve_up_not_supplied_cost-cost_participation_tertiary1_reserve_up) * yc
                       + (tertiary2_reserve_up_not_supplied_cost-cost_participation_tertiary2_reserve_up) * yd
                        + (primary_reserve_down_not_supplied_cost-cost_participation_primary_reserve_down) * za
                         + (secondary_reserve_down_not_supplied_cost-cost_participation_secondary_reserve_down) * zb
                          + (tertiary1_reserve_down_not_supplied_cost-cost_participation_tertiary1_reserve_down) * zc 
                           + (tertiary2_reserve_down_not_supplied_cost-cost_participation_tertiary2_reserve_down) * zd
                            + (ens_cost - cost - spillage_cost) * x)

    # Solve the system.
    status = solver.Solve()


    energy_generation_classique = max(nbr_on_classic * p_min + generation_reserve_down,
                                      min(energy_generation,
                                          nbr_on_classic * p_max - generation_reserve_up))
    gain = fixed_cost  + (cost + spillage_cost) * (energy_generation_classique - energy_generation) - startup_cost
    
    
    if solver.Objective().Value() < gain:  
        return nbr_on
    return nbr_on_classic


def arrondi_opti_sans_start_up(
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
    cost_participation_primary_reserve_up : float,
    cost_participation_primary_reserve_down : float,
    cost_participation_secondary_reserve_up : float,
    cost_participation_secondary_reserve_down : float,
    cost_participation_tertiary1_reserve_up : float,
    cost_participation_tertiary1_reserve_down : float,
    cost_participation_tertiary2_reserve_up : float,        
    cost_participation_tertiary2_reserve_down : float,
    spillage_cost : float,
    ens_cost : float,
    primary_reserve_up_not_supplied_cost : float,
    primary_reserve_down_not_supplied_cost : float,
    secondary_reserve_up_not_supplied_cost : float,
    secondary_reserve_down_not_supplied_cost : float,
    tertiary1_reserve_up_not_supplied_cost : float,
    tertiary1_reserve_down_not_supplied_cost : float,
    tertiary2_reserve_up_not_supplied_cost : float,
    tertiary2_reserve_down_not_supplied_cost : float,
) -> int:
    
    nbr_on = floor(round(nbr_on_float,12))
    nbr_on_classic = ceil(round(nbr_on_float,12))

    solver = lp.Solver.CreateSolver("SCIP")

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

    generation_reserve_up = generation_reserve_up_primary + generation_reserve_up_secondary + generation_reserve_up_tertiary1 + generation_reserve_up_tertiary2
    generation_reserve_down = generation_reserve_down_primary + generation_reserve_down_secondary + generation_reserve_down_tertiary1 + generation_reserve_down_tertiary2

    borne_max = max(0,generation_reserve_up + energy_generation - nbr_on * p_max)
    borne_min = energy_generation - generation_reserve_down - nbr_on*p_min
    
    solver.Add(1 * x + 1 * ya + 1 * yb + 1 * yc + 1 * yd >= borne_max)
    solver.Add(1 * x - 1 * za - 1 * zb - 1 * zc - 1 * zd <= borne_min)


    solver.Minimize((primary_reserve_up_not_supplied_cost-cost_participation_primary_reserve_up) * ya
                     + (secondary_reserve_up_not_supplied_cost-cost_participation_secondary_reserve_up) * yb
                      + (tertiary1_reserve_up_not_supplied_cost-cost_participation_tertiary1_reserve_up) * yc
                       + (tertiary2_reserve_up_not_supplied_cost-cost_participation_tertiary2_reserve_up) * yd
                        + (primary_reserve_down_not_supplied_cost-cost_participation_primary_reserve_down) * za
                         + (secondary_reserve_down_not_supplied_cost-cost_participation_secondary_reserve_down) * zb
                          + (tertiary1_reserve_down_not_supplied_cost-cost_participation_tertiary1_reserve_down) * zc 
                           + (tertiary2_reserve_down_not_supplied_cost-cost_participation_tertiary2_reserve_down) * zd
                            + (ens_cost - cost - spillage_cost) * x)

    # Solve the system.
    status = solver.Solve()

    a = x.SolutionValue()
    b = ya.SolutionValue()
    c = za.SolutionValue()
    d = solver.Objective().Value()

    # if nbr_on_float > 12 and p_max > 600:
    #     e = f,
    #     g = e

    energy_generation_classique = max(nbr_on_classic * p_min + generation_reserve_down,
                                      min(energy_generation,
                                          nbr_on_classic * p_max - generation_reserve_up))
    gain = fixed_cost  + (cost + spillage_cost) * (energy_generation_classique - energy_generation)
    if solver.Objective().Value() <= gain:  
        return nbr_on
    return nbr_on_classic


def nouvelle_arrondi(
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
    cost_participation_primary_reserve_up : float,
    cost_participation_primary_reserve_down : float,
    cost_participation_secondary_reserve_up : float,
    cost_participation_secondary_reserve_down : float,
    cost_participation_tertiary1_reserve_up : float,
    cost_participation_tertiary1_reserve_down : float,
    cost_participation_tertiary2_reserve_up : float,        
    cost_participation_tertiary2_reserve_down : float,
    spillage_cost : float,
    ens_cost : float,
    primary_reserve_up_not_supplied_cost : float,
    primary_reserve_down_not_supplied_cost : float,
    secondary_reserve_up_not_supplied_cost : float,
    secondary_reserve_down_not_supplied_cost : float,
    tertiary1_reserve_up_not_supplied_cost : float,
    tertiary1_reserve_down_not_supplied_cost : float,
    tertiary2_reserve_up_not_supplied_cost : float,
    tertiary2_reserve_down_not_supplied_cost : float,
) -> int:
    
    nbr_on = floor(round(nbr_on_float,12))
    nbr_on_classic = ceil(round(nbr_on_float,12))

    UNSP_primary_up = max(0,generation_reserve_up_primary-nbr_on*participation_max_primary_reserve_up)
    UNSP_primary_down = max(0,generation_reserve_down_primary-nbr_on*participation_max_primary_reserve_down)
    UNSP_secondary_up = max(0,generation_reserve_up_secondary-nbr_on*participation_max_secondary_reserve_up)
    UNSP_secondary_down = max(0,generation_reserve_down_secondary-nbr_on*participation_max_secondary_reserve_down)
    UNSP_tertiary1_up = max(0,generation_reserve_up_tertiary1-nbr_on*participation_max_tertiary1_reserve_up)
    UNSP_tertiary1_down = max(0,generation_reserve_down_tertiary1-nbr_on*participation_max_tertiary1_reserve_down)
    UNSP_tertiary2_up = max(0,generation_reserve_up_tertiary2-nbr_on*participation_max_tertiary2_reserve_up)
    UNSP_tertiary2_down = max(0,generation_reserve_down_tertiary2-nbr_on*participation_max_tertiary2_reserve_down)
    
    generation_reserve_up = generation_reserve_up_primary + generation_reserve_up_secondary + generation_reserve_up_tertiary1 + generation_reserve_up_tertiary2
    generation_reserve_down = generation_reserve_down_primary + generation_reserve_down_secondary + generation_reserve_down_tertiary1 + generation_reserve_down_tertiary2

    UNSP_prod = max(0,energy_generation+generation_reserve_up-nbr_on*p_max)-UNSP_primary_up-UNSP_secondary_up-UNSP_tertiary1_up-UNSP_tertiary2_up
    
    cout = primary_reserve_up_not_supplied_cost*UNSP_primary_up + primary_reserve_down_not_supplied_cost*UNSP_primary_down+ secondary_reserve_up_not_supplied_cost*UNSP_secondary_up + secondary_reserve_down_not_supplied_cost*UNSP_secondary_down+ tertiary1_reserve_up_not_supplied_cost*UNSP_tertiary1_up + tertiary1_reserve_down_not_supplied_cost*UNSP_tertiary1_down+tertiary2_reserve_up_not_supplied_cost*UNSP_tertiary2_up + tertiary2_reserve_down_not_supplied_cost*UNSP_tertiary2_down+ (ens_cost-(cost+spillage_cost))*UNSP_prod
    

    energy_generation_classique = max(nbr_on_classic * p_min + generation_reserve_down,
                                      min(energy_generation,
                                          nbr_on_classic * p_max - generation_reserve_up))
    gain = fixed_cost  + (cost + spillage_cost) * ( energy_generation_classique - energy_generation) - startup_cost
    if cout < gain:
        return(nbr_on)
    return(nbr_on_classic)
    
def old_arrondi(
    nbr_on_float : float,
    energy_generation : Optional[float] = 0,
    generation_reserve_up_primary : Optional[float] = 0,
    generation_reserve_down_primary : Optional[float] = 0,
    generation_reserve_up_secondary : Optional[float] = 0,
    generation_reserve_down_secondary : Optional[float] = 0,
    generation_reserve_up_tertiary1 : Optional[float] = 0,
    generation_reserve_down_tertiary1 : Optional[float] = 0,
    generation_reserve_up_tertiary2 : Optional[float] = 0,
    generation_reserve_down_tertiary2 : Optional[float] = 0,
    p_max : Optional[float] = 0,
    p_min : Optional[float] = 0,
    participation_max_primary_reserve_up : Optional[float] = 0,
    participation_max_primary_reserve_down : Optional[float] = 0,
    participation_max_secondary_reserve_up : Optional[float] = 0,
    participation_max_secondary_reserve_down : Optional[float] = 0,
    participation_max_tertiary1_reserve_up : Optional[float] = 0,
    participation_max_tertiary1_reserve_down : Optional[float] = 0,
    participation_max_tertiary2_reserve_up : Optional[float] = 0,
    participation_max_tertiary2_reserve_down : Optional[float] = 0,
    cost : Optional[float] = 0,
    startup_cost : Optional[float] = 0,
    fixed_cost : Optional[float] = 0,
    cost_participation_primary_reserve_up : Optional[float] = 0,
    cost_participation_primary_reserve_down : Optional[float] = 0,
    cost_participation_secondary_reserve_up : Optional[float] = 0,
    cost_participation_secondary_reserve_down : Optional[float] = 0,
    cost_participation_tertiary1_reserve_up : Optional[float] = 0,
    cost_participation_tertiary1_reserve_down : Optional[float] = 0,
    cost_participation_tertiary2_reserve_up : Optional[float] = 0,       
    cost_participation_tertiary2_reserve_down : Optional[float] = 0,
    spillage_cost : Optional[float] = 0,
    ens_cost : Optional[float] = 0,
    primary_reserve_up_not_supplied_cost : Optional[float] = 0,
    primary_reserve_down_not_supplied_cost : Optional[float] = 0,
    secondary_reserve_up_not_supplied_cost : Optional[float] = 0,
    secondary_reserve_down_not_supplied_cost : Optional[float] = 0,
    tertiary1_reserve_up_not_supplied_cost : Optional[float] = 0,
    tertiary1_reserve_down_not_supplied_cost : Optional[float] = 0,
    tertiary2_reserve_up_not_supplied_cost : Optional[float] = 0,
    tertiary2_reserve_down_not_supplied_cost : Optional[float] = 0,
) -> int:
    
    nbr_on = ceil(round(nbr_on_float,12))
    return(nbr_on)
