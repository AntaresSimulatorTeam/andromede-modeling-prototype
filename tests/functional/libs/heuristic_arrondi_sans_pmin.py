from math import ceil,floor
from typing import  List

import ortools.linear_solver.pywraplp as lp


def old_arrondi(
    dictionnaire_valeur : dict[List[float]],
    t : int
) -> List[int]:
    
    nbr_on_float = dictionnaire_valeur["nb_on"][t]
    nbr_on = ceil(round(nbr_on_float,12))
    return[nbr_on]


def defaillance(
    version : str,
    dictionnaire_valeur : dict[List[float]],
    t : int,
    ) -> List[int]:
    
    nbr_on_float = dictionnaire_valeur["nb_on"][t]
    energy_generation = dictionnaire_valeur["energy_generation"][t]
    generation_reserve_up_primary_on = dictionnaire_valeur["generation_reserve_up_primary_on"][t]
    generation_reserve_down_primary = dictionnaire_valeur["generation_reserve_down_primary"][t]
    generation_reserve_up_secondary_on = dictionnaire_valeur["generation_reserve_up_secondary_on"][t]
    generation_reserve_down_secondary = dictionnaire_valeur["generation_reserve_down_secondary"][t]
    generation_reserve_up_tertiary1_on = dictionnaire_valeur["generation_reserve_up_tertiary1_on"][t]
    generation_reserve_down_tertiary1 = dictionnaire_valeur["generation_reserve_down_tertiary1"][t]
    generation_reserve_up_tertiary2_on = dictionnaire_valeur["generation_reserve_up_tertiary2_on"][t]
    generation_reserve_down_tertiary2 = dictionnaire_valeur["generation_reserve_down_tertiary2"][t]
    p_max = dictionnaire_valeur["p_max"][t]
    p_min = dictionnaire_valeur["p_min"][t]
    nbr_units_max = dictionnaire_valeur["nb_units_max_invisible"][t]
    participation_max_primary_reserve_up_on = dictionnaire_valeur["participation_max_primary_reserve_up_on"][t]
    participation_max_primary_reserve_down = dictionnaire_valeur["participation_max_primary_reserve_down"][t]
    participation_max_secondary_reserve_up_on = dictionnaire_valeur["participation_max_secondary_reserve_up_on"][t]
    participation_max_secondary_reserve_down = dictionnaire_valeur["participation_max_secondary_reserve_down"][t]
    participation_max_tertiary1_reserve_up_on = dictionnaire_valeur["participation_max_tertiary1_reserve_up_on"][t]
    participation_max_tertiary1_reserve_down = dictionnaire_valeur["participation_max_tertiary1_reserve_down"][t]
    participation_max_tertiary2_reserve_up_on = dictionnaire_valeur["participation_max_tertiary2_reserve_up_on"][t]
    participation_max_tertiary2_reserve_down = dictionnaire_valeur["participation_max_tertiary2_reserve_down"][t]
    cost = dictionnaire_valeur["cost"][t]
    startup_cost = dictionnaire_valeur["startup_cost"][t]
    fixed_cost = dictionnaire_valeur["fixed_cost"][t]
    cost_participation_primary_reserve_up_on = dictionnaire_valeur["cost_participation_primary_reserve_up_on"][t]
    cost_participation_primary_reserve_down = dictionnaire_valeur["cost_participation_primary_reserve_down"][t]
    cost_participation_secondary_reserve_up_on = dictionnaire_valeur["cost_participation_secondary_reserve_up_on"][t]
    cost_participation_secondary_reserve_down = dictionnaire_valeur["cost_participation_secondary_reserve_down"][t]
    cost_participation_tertiary1_reserve_up_on = dictionnaire_valeur["cost_participation_tertiary1_reserve_up_on"][t]
    cost_participation_tertiary1_reserve_down = dictionnaire_valeur["cost_participation_tertiary1_reserve_down"][t]
    cost_participation_tertiary2_reserve_up_on = dictionnaire_valeur["cost_participation_tertiary2_reserve_up_on"][t]         
    cost_participation_tertiary2_reserve_down = dictionnaire_valeur["cost_participation_tertiary2_reserve_down"][t]
    spillage_cost = dictionnaire_valeur["spillage_cost"][t]
    ens_cost = dictionnaire_valeur["ens_cost"][t]
    primary_reserve_up_not_supplied_cost = dictionnaire_valeur["primary_reserve_up_not_supplied_cost"][t]
    primary_reserve_down_not_supplied_cost = dictionnaire_valeur["primary_reserve_down_not_supplied_cost"][t]
    secondary_reserve_up_not_supplied_cost = dictionnaire_valeur["secondary_reserve_up_not_supplied_cost"][t]
    secondary_reserve_down_not_supplied_cost = dictionnaire_valeur["secondary_reserve_down_not_supplied_cost"][t]
    tertiary1_reserve_up_not_supplied_cost = dictionnaire_valeur["tertiary1_reserve_up_not_supplied_cost"][t]
    tertiary1_reserve_down_not_supplied_cost = dictionnaire_valeur["tertiary1_reserve_down_not_supplied_cost"][t]
    tertiary2_reserve_up_not_supplied_cost = dictionnaire_valeur["tertiary2_reserve_up_not_supplied_cost"][t]
    tertiary2_reserve_down_not_supplied_cost = dictionnaire_valeur["tertiary2_reserve_down_not_supplied_cost"][t]
    max_generating = dictionnaire_valeur["max_generating"][t]
    min_generating = dictionnaire_valeur["min_generating"][t]

    nbr_on = floor(round(nbr_on_float,12))
    nbr_on_classic = min(ceil(round(nbr_on_float,12)),nbr_units_max)

    if nbr_on * p_min < min_generating:
        return([nbr_on_classic,nbr_on_classic,0,0,startup_cost])

    solver = lp.Solver.CreateSolver("SCIP")

    UNSP_primary_up_min = max(0,generation_reserve_up_primary_on-nbr_on*participation_max_primary_reserve_up_on)  
    UNSP_primary_down_min = max(0,generation_reserve_down_primary-nbr_on*participation_max_primary_reserve_down)
    UNSP_secondary_up_min = max(0,generation_reserve_up_secondary_on-nbr_on*participation_max_secondary_reserve_up_on)  
    UNSP_secondary_down_min = max(0,generation_reserve_down_secondary-nbr_on*participation_max_secondary_reserve_down)
    UNSP_tertiary1_up_min = max(0,generation_reserve_up_tertiary1_on-nbr_on*participation_max_tertiary1_reserve_up_on)  
    UNSP_tertiary1_down_min = max(0,generation_reserve_down_tertiary1-nbr_on*participation_max_tertiary1_reserve_down)
    UNSP_tertiary2_up_min = max(0,generation_reserve_up_tertiary2_on-nbr_on*participation_max_tertiary2_reserve_up_on)  
    UNSP_tertiary2_down_min = max(0,generation_reserve_down_tertiary2-nbr_on*participation_max_tertiary2_reserve_down)

    x = solver.NumVar(0, energy_generation, "x") #UNSP_prod
    ya = solver.NumVar(UNSP_primary_up_min, generation_reserve_up_primary_on, "ya") #UNSP_res+
    za = solver.NumVar(UNSP_primary_down_min, generation_reserve_down_primary, "za")    #UNSP_res-
    yb = solver.NumVar(UNSP_secondary_up_min, generation_reserve_up_secondary_on, "yb") #UNSP_res+
    zb = solver.NumVar(UNSP_secondary_down_min, generation_reserve_down_secondary, "zb")    #UNSP_res-
    yc = solver.NumVar(UNSP_tertiary1_up_min, generation_reserve_up_tertiary1_on, "yc") #UNSP_res+
    zc = solver.NumVar(UNSP_tertiary1_down_min, generation_reserve_down_tertiary1, "zc")    #UNSP_res-
    yd = solver.NumVar(UNSP_tertiary2_up_min, generation_reserve_up_tertiary2_on, "yd") #UNSP_res+
    zd = solver.NumVar(UNSP_tertiary2_down_min, generation_reserve_down_tertiary2, "zd")    #UNSP_res-

    generation_reserve_up = generation_reserve_up_primary_on + generation_reserve_up_secondary_on + generation_reserve_up_tertiary1_on + generation_reserve_up_tertiary2_on
    generation_reserve_down = generation_reserve_down_primary + generation_reserve_down_secondary + generation_reserve_down_tertiary1 + generation_reserve_down_tertiary2

    borne_max = max(0,generation_reserve_up + energy_generation - nbr_on * p_max,generation_reserve_up + energy_generation - max_generating)
    borne_min = min(energy_generation - generation_reserve_down - nbr_on * p_min,energy_generation - generation_reserve_down - min_generating)
    
    solver.Add(1 * x + 1 * ya + 1 * yb + 1 * yc + 1 * yd >= borne_max)
    solver.Add(1 * x - 1 * za - 1 * zb - 1 * zc - 1 * zd <= borne_min)


    solver.Minimize((primary_reserve_up_not_supplied_cost-cost_participation_primary_reserve_up_on) * ya
                     + (secondary_reserve_up_not_supplied_cost-cost_participation_secondary_reserve_up_on) * yb
                      + (tertiary1_reserve_up_not_supplied_cost-cost_participation_tertiary1_reserve_up_on) * yc
                       + (tertiary2_reserve_up_not_supplied_cost-cost_participation_tertiary2_reserve_up_on) * yd
                        + (primary_reserve_down_not_supplied_cost-cost_participation_primary_reserve_down) * za
                         + (secondary_reserve_down_not_supplied_cost-cost_participation_secondary_reserve_down) * zb
                          + (tertiary1_reserve_down_not_supplied_cost-cost_participation_tertiary1_reserve_down) * zc 
                           + (tertiary2_reserve_down_not_supplied_cost-cost_participation_tertiary2_reserve_down) * zd
                            + (ens_cost - cost) * x)

    # Solve the system.
    status = solver.Solve()

    cout = solver.Objective().Value()


    energy_generation_classique = max(nbr_on_classic * p_min + generation_reserve_down,
                                      min(energy_generation,
                                          nbr_on_classic * p_max - generation_reserve_up))
    if version == "gain":
        gain = fixed_cost  + startup_cost + (cost + spillage_cost) * (energy_generation_classique - energy_generation)
    elif version == "sans":
        gain = fixed_cost  + (cost + spillage_cost) * (energy_generation_classique - energy_generation)
    elif version == "perte":
        gain = fixed_cost  - startup_cost + (cost + spillage_cost) * (energy_generation_classique - energy_generation)
    if cout <= gain:  
        return [nbr_on,nbr_on,cout,gain,startup_cost]
    return [nbr_on_classic,nbr_on,cout,gain,startup_cost]


def determination_generations_sans_pmin(
    nbr_on : int,
    dictionnaire_valeur : dict[List[float]],
    t : int,
    ) -> List[int]:

    energy_generation = dictionnaire_valeur["energy_generation"][t]
    generation_reserve_up_primary_on = dictionnaire_valeur["generation_reserve_up_primary_on"][t]
    generation_reserve_up_primary_off = dictionnaire_valeur["generation_reserve_up_primary_off"][t]
    generation_reserve_down_primary = dictionnaire_valeur["generation_reserve_down_primary"][t]
    generation_reserve_up_secondary_on = dictionnaire_valeur["generation_reserve_up_secondary_on"][t]
    generation_reserve_up_secondary_off = dictionnaire_valeur["generation_reserve_up_secondary_off"][t]
    generation_reserve_down_secondary = dictionnaire_valeur["generation_reserve_down_secondary"][t]
    generation_reserve_up_tertiary1_on = dictionnaire_valeur["generation_reserve_up_tertiary1_on"][t]
    generation_reserve_up_tertiary1_off = dictionnaire_valeur["generation_reserve_up_tertiary1_off"][t]
    generation_reserve_down_tertiary1 = dictionnaire_valeur["generation_reserve_down_tertiary1"][t]
    generation_reserve_up_tertiary2_on = dictionnaire_valeur["generation_reserve_up_tertiary2_on"][t]
    generation_reserve_up_tertiary2_off = dictionnaire_valeur["generation_reserve_up_tertiary2_off"][t]
    generation_reserve_down_tertiary2 = dictionnaire_valeur["generation_reserve_down_tertiary2"][t]
    p_max = dictionnaire_valeur["p_max"][t]
    p_min = dictionnaire_valeur["p_min"][t]
    nb_units_max_invisible = dictionnaire_valeur["nb_units_max_invisible"][t]
    participation_max_primary_reserve_up_on = dictionnaire_valeur["participation_max_primary_reserve_up_on"][t]
    participation_max_primary_reserve_up_off = dictionnaire_valeur["participation_max_primary_reserve_up_off"][t]
    participation_max_primary_reserve_down = dictionnaire_valeur["participation_max_primary_reserve_down"][t]
    participation_max_secondary_reserve_up_on = dictionnaire_valeur["participation_max_secondary_reserve_up_on"][t]
    participation_max_secondary_reserve_up_off = dictionnaire_valeur["participation_max_secondary_reserve_up_off"][t]
    participation_max_secondary_reserve_down = dictionnaire_valeur["participation_max_secondary_reserve_down"][t]
    participation_max_tertiary1_reserve_up_on = dictionnaire_valeur["participation_max_tertiary1_reserve_up_on"][t]
    participation_max_tertiary1_reserve_up_off = dictionnaire_valeur["participation_max_tertiary1_reserve_up_off"][t]
    participation_max_tertiary1_reserve_down = dictionnaire_valeur["participation_max_tertiary1_reserve_down"][t]
    participation_max_tertiary2_reserve_up_on = dictionnaire_valeur["participation_max_tertiary2_reserve_up_on"][t]
    participation_max_tertiary2_reserve_up_off = dictionnaire_valeur["participation_max_tertiary2_reserve_up_off"][t]
    participation_max_tertiary2_reserve_down = dictionnaire_valeur["participation_max_tertiary2_reserve_down"][t]
    cost = dictionnaire_valeur["cost"][t]
    fixed_cost = dictionnaire_valeur["fixed_cost"][t]
    cost_participation_primary_reserve_up_on = dictionnaire_valeur["cost_participation_primary_reserve_up_on"][t]
    cost_participation_primary_reserve_up_off = dictionnaire_valeur["cost_participation_primary_reserve_up_off"][t]
    cost_participation_primary_reserve_down = dictionnaire_valeur["cost_participation_primary_reserve_down"][t]
    cost_participation_secondary_reserve_up_on = dictionnaire_valeur["cost_participation_secondary_reserve_up_on"][t]
    cost_participation_secondary_reserve_up_off = dictionnaire_valeur["cost_participation_secondary_reserve_up_off"][t]
    cost_participation_secondary_reserve_down = dictionnaire_valeur["cost_participation_secondary_reserve_down"][t]
    cost_participation_tertiary1_reserve_up_on = dictionnaire_valeur["cost_participation_tertiary1_reserve_up_on"][t]
    cost_participation_tertiary1_reserve_up_off = dictionnaire_valeur["cost_participation_tertiary1_reserve_up_off"][t]
    cost_participation_tertiary1_reserve_down = dictionnaire_valeur["cost_participation_tertiary1_reserve_down"][t]
    cost_participation_tertiary2_reserve_up_on = dictionnaire_valeur["cost_participation_tertiary2_reserve_up_on"][t]   
    cost_participation_tertiary2_reserve_up_off = dictionnaire_valeur["cost_participation_tertiary2_reserve_up_off"][t]        
    cost_participation_tertiary2_reserve_down = dictionnaire_valeur["cost_participation_tertiary2_reserve_down"][t]
    spillage_cost = dictionnaire_valeur["spillage_cost"][t]
    ens_cost = dictionnaire_valeur["ens_cost"][t]
    primary_reserve_up_not_supplied_cost = dictionnaire_valeur["primary_reserve_up_not_supplied_cost"][t]
    primary_reserve_down_not_supplied_cost = dictionnaire_valeur["primary_reserve_down_not_supplied_cost"][t]
    secondary_reserve_up_not_supplied_cost = dictionnaire_valeur["secondary_reserve_up_not_supplied_cost"][t]
    secondary_reserve_down_not_supplied_cost = dictionnaire_valeur["secondary_reserve_down_not_supplied_cost"][t]
    tertiary1_reserve_up_not_supplied_cost = dictionnaire_valeur["tertiary1_reserve_up_not_supplied_cost"][t]
    tertiary1_reserve_down_not_supplied_cost = dictionnaire_valeur["tertiary1_reserve_down_not_supplied_cost"][t]
    tertiary2_reserve_up_not_supplied_cost = dictionnaire_valeur["tertiary2_reserve_up_not_supplied_cost"][t]
    tertiary2_reserve_down_not_supplied_cost = dictionnaire_valeur["tertiary2_reserve_down_not_supplied_cost"][t]
    primary_reserve_up_oversupplied_cost = dictionnaire_valeur["primary_reserve_up_oversupplied_cost"][t]
    primary_reserve_down_oversupplied_cost = dictionnaire_valeur["primary_reserve_down_oversupplied_cost"][t]
    secondary_reserve_up_oversupplied_cost = dictionnaire_valeur["secondary_reserve_up_oversupplied_cost"][t]
    secondary_reserve_down_oversupplied_cost = dictionnaire_valeur["secondary_reserve_down_oversupplied_cost"][t]
    tertiary1_reserve_up_oversupplied_cost = dictionnaire_valeur["tertiary1_reserve_up_oversupplied_cost"][t]
    tertiary1_reserve_down_oversupplied_cost = dictionnaire_valeur["tertiary1_reserve_down_oversupplied_cost"][t]
    tertiary2_reserve_up_oversupplied_cost = dictionnaire_valeur["tertiary2_reserve_up_oversupplied_cost"][t]
    tertiary2_reserve_down_oversupplied_cost = dictionnaire_valeur["tertiary2_reserve_down_oversupplied_cost"][t]
    max_generating = dictionnaire_valeur["max_generating"][t]
    min_generating = dictionnaire_valeur["min_generating"][t]


    
    solver = lp.Solver.CreateSolver("SCIP")
        
    generation_reserve_up_primary = generation_reserve_up_primary_on + generation_reserve_up_primary_off
    generation_reserve_up_secondary = generation_reserve_up_secondary_on + generation_reserve_up_secondary_off
    generation_reserve_up_tertiary1 = generation_reserve_up_tertiary1_on + generation_reserve_up_tertiary1_off
    generation_reserve_up_tertiary2 = generation_reserve_up_tertiary2_on + generation_reserve_up_tertiary2_off
    nbr_off = nb_units_max_invisible - nbr_on

    x = solver.NumVar(0, min(energy_generation,nbr_on * p_max), "x") #Prod energie
    SPILL_x = solver.NumVar(0, nbr_on * p_max, "spillx")
    yaon = solver.NumVar(0, nbr_on * participation_max_primary_reserve_up_on, "yaon") #Prod_res+_on
    SPILL_yaon = solver.NumVar(0, nbr_on * p_max, "spillyaon")
    yaoff = solver.NumVar(0, nbr_off * participation_max_primary_reserve_up_off, "yaoff") #Prod_res+_off
    SPILL_yaoff = solver.NumVar(0, nbr_off * p_max, "spillyaoff")
    ybon = solver.NumVar(0, nbr_on * participation_max_secondary_reserve_up_on, "yaon") #Prod_res+_on
    SPILL_ybon = solver.NumVar(0, nbr_on * p_max, "spillybon")
    yboff = solver.NumVar(0, nbr_off * participation_max_secondary_reserve_up_off, "yaoff") #Prod_res+_on
    SPILL_yboff = solver.NumVar(0, nbr_off * p_max, "spillyboff")
    ycon = solver.NumVar(0, nbr_on * participation_max_tertiary1_reserve_up_on, "yaon") #Prod_res+_on
    SPILL_ycon = solver.NumVar(0, nbr_on * p_max, "spillycon")
    ycoff = solver.NumVar(0, nbr_off * participation_max_tertiary1_reserve_up_off, "yaoff") #Prod_res+_off
    SPILL_ycoff = solver.NumVar(0, nbr_off * p_max, "spillycoff")
    ydon = solver.NumVar(0, nbr_on * participation_max_tertiary2_reserve_up_on, "yaon") #Prod_res+_on
    SPILL_ydon = solver.NumVar(0, nbr_on * p_max, "spillydon")
    ydoff = solver.NumVar(0, nbr_off * participation_max_tertiary2_reserve_up_off, "yaoff") #Prod_res+_off
    SPILL_ydoff = solver.NumVar(0, nbr_off * p_max, "spillydoff")
    za = solver.NumVar(0, generation_reserve_down_primary, "za")    #Prod_res-
    SPILL_za = solver.NumVar(0, nbr_on * p_max, "spillza")
    zb = solver.NumVar(0, generation_reserve_down_secondary, "zb")    #Prod_res-
    SPILL_zb = solver.NumVar(0, nbr_on * p_max, "spillzb")
    zc = solver.NumVar(0, generation_reserve_down_tertiary1, "zc")    #Prod_res-
    SPILL_zc = solver.NumVar(0, nbr_on * p_max, "spillzc")
    zd = solver.NumVar(0, generation_reserve_down_tertiary2, "zd")    #Prod_res-
    SPILL_zd = solver.NumVar(0, nbr_on * p_max, "spillzd")
        
    borne_max_on = nbr_on * p_max
    borne_max_off = (nb_units_max_invisible-nbr_on) * p_max
    borne_min = min(nbr_on * p_min,min_generating)
    participation_max_primary_off = nbr_off * participation_max_primary_reserve_up_off
    participation_max_secondary_off = nbr_off * participation_max_secondary_reserve_up_off
    participation_max_tertiary1_off = nbr_off * participation_max_tertiary1_reserve_up_off
    participation_max_tertiary2_off = nbr_off * participation_max_tertiary2_reserve_up_off
    participation_max_primary_on = nbr_on* participation_max_primary_reserve_up_on
    participation_max_secondary_on = nbr_on * participation_max_secondary_reserve_up_on
    participation_max_tertiary1_on = nbr_on * participation_max_tertiary1_reserve_up_on
    participation_max_tertiary2_on = nbr_on * participation_max_tertiary2_reserve_up_on
    participation_max_primary_down = nbr_on* participation_max_primary_reserve_down
    participation_max_secondary_down = nbr_on * participation_max_secondary_reserve_down
    participation_max_tertiary1_down = nbr_on * participation_max_tertiary1_reserve_down
    participation_max_tertiary2_down = nbr_on * participation_max_tertiary2_reserve_down
        
    solver.Add(1 * x + 1 * SPILL_x + 1 * yaon + 1 * SPILL_yaon + 1 * ybon + 1 * SPILL_ybon + 1 * ycon + 1 * SPILL_ycon + 1 * ydon + 1 * SPILL_ydon <= borne_max_on)
    solver.Add(1 * x + 1 * SPILL_x + 1 * yaon + 1 * SPILL_yaon + 1 * ybon + 1 * SPILL_ybon + 1 * ycon + 1 * SPILL_ycon + 1 * ydon + 1 * SPILL_ydon 
               + 1 * yaoff  + 1 * SPILL_yaoff + 1 * yboff  + 1 * SPILL_yboff + 1 * ycoff  + 1 * SPILL_ycoff + 1 * ydoff  + 1 * SPILL_ydoff <= max_generating)
    solver.Add(1 * x + 1 * SPILL_x - 1 * za - 1 * SPILL_za - 1 * zb - 1 * SPILL_zb - 1 * zc - 1 * SPILL_zc - 1 * zd - 1 * SPILL_zd >= borne_min)
    solver.Add(1 * yaoff  + 1 * SPILL_yaoff + 1 * yboff  + 1 * SPILL_yboff + 1 * ycoff  + 1 * SPILL_ycoff + 1 * ydoff  + 1 * SPILL_ydoff <= borne_max_off)
    solver.Add(1 * yaoff + 1 * SPILL_yaoff <= participation_max_primary_off)
    solver.Add(1 * yboff + 1 * SPILL_yboff <= participation_max_secondary_off)
    solver.Add(1 * ycoff + 1 * SPILL_ycoff <= participation_max_tertiary1_off)
    solver.Add(1 * ydoff + 1 * SPILL_ydoff <= participation_max_tertiary2_off)
    solver.Add(1 * yaon + 1 * SPILL_yaon <= participation_max_primary_on)
    solver.Add(1 * ybon + 1 * SPILL_ybon <= participation_max_secondary_on)
    solver.Add(1 * ycon + 1 * SPILL_ycon <= participation_max_tertiary1_on)
    solver.Add(1 * ydon + 1 * SPILL_ydon <= participation_max_tertiary2_on)
    solver.Add(1 * za  + 1 * SPILL_za  <= participation_max_primary_down)
    solver.Add(1 * zb  + 1 * SPILL_zb  <= participation_max_secondary_down)
    solver.Add(1 * zc  + 1 * SPILL_zc  <= participation_max_tertiary1_down)
    solver.Add(1 * zd  + 1 * SPILL_zd  <= participation_max_tertiary2_down)
    solver.Add(1 * yaoff + 1 * yaon <= generation_reserve_up_primary)
    solver.Add(1 * yboff + 1 * ybon <= generation_reserve_up_secondary)
    solver.Add(1 * ycoff + 1 * ycon <= generation_reserve_up_tertiary1)
    solver.Add(1 * ydoff + 1 * ydon <= generation_reserve_up_tertiary2)

    solver.Minimize(cost_participation_primary_reserve_up_on * (yaon + SPILL_yaon)
                    + cost_participation_primary_reserve_up_off * (yaoff + SPILL_yaoff)
                    + primary_reserve_up_not_supplied_cost * (generation_reserve_up_primary - yaon - yaoff)
                    + cost_participation_secondary_reserve_up_on * (ybon + SPILL_ybon)
                    + cost_participation_secondary_reserve_up_off * (yboff + SPILL_yboff)
                    + secondary_reserve_up_not_supplied_cost * (generation_reserve_up_secondary - ybon - yboff)
                    + cost_participation_tertiary1_reserve_up_on * (ycon + SPILL_ycon)
                    + cost_participation_tertiary1_reserve_up_off * (ycoff + SPILL_ycoff)
                    + tertiary1_reserve_up_not_supplied_cost * (generation_reserve_up_tertiary1 - ycon - ycoff)
                    + cost_participation_tertiary2_reserve_up_on * (ydon + SPILL_ydon)
                    + cost_participation_tertiary2_reserve_up_off * (ydoff + SPILL_ydoff)
                    + tertiary2_reserve_up_not_supplied_cost * (generation_reserve_up_tertiary2 - ydon - ydoff)
                    + cost_participation_primary_reserve_down * (za + SPILL_za)
                    + primary_reserve_down_not_supplied_cost * (generation_reserve_down_primary - za)
                    + cost_participation_secondary_reserve_down * (zb + SPILL_zb)
                    + secondary_reserve_down_not_supplied_cost * (generation_reserve_down_secondary - zb)
                    + cost_participation_tertiary1_reserve_down * (zc + SPILL_zc)
                    + tertiary1_reserve_down_not_supplied_cost * (generation_reserve_down_tertiary1 - zc)
                    + cost_participation_tertiary2_reserve_down * (zd + SPILL_zd)
                    + tertiary2_reserve_down_not_supplied_cost * (generation_reserve_down_tertiary2 - zd)
                    + cost * (x + SPILL_x)
                    + ens_cost * (energy_generation - x)
                    + spillage_cost * SPILL_x
                    + primary_reserve_up_oversupplied_cost * (SPILL_yaon + SPILL_yaoff)
                    + secondary_reserve_up_oversupplied_cost * (SPILL_ybon + SPILL_yboff)
                    + tertiary1_reserve_up_oversupplied_cost * (SPILL_ycon + SPILL_ycoff)
                    + tertiary2_reserve_up_oversupplied_cost * (SPILL_ydon + SPILL_ydoff)
                    + primary_reserve_down_oversupplied_cost * SPILL_za
                    + secondary_reserve_down_oversupplied_cost * SPILL_zb
                    + tertiary1_reserve_down_oversupplied_cost * SPILL_zc
                    + tertiary2_reserve_down_oversupplied_cost * SPILL_zd
                    + fixed_cost * nbr_on)

    # Solve the system.
    status = solver.Solve()

    prod = x.SolutionValue() + SPILL_x.SolutionValue()
    primary_up_on = yaon.SolutionValue() + SPILL_yaon.SolutionValue()
    primary_up_off = yaoff.SolutionValue() + SPILL_yaoff.SolutionValue()
    primary_down = za.SolutionValue() + SPILL_za.SolutionValue()
    secondary_up_on = ybon.SolutionValue() + SPILL_ybon.SolutionValue()
    secondary_up_off = yboff.SolutionValue() + SPILL_yboff.SolutionValue()
    secondary_down = zb.SolutionValue() + SPILL_zb.SolutionValue()
    tertiary1_up_on = ycon.SolutionValue() + SPILL_ycon.SolutionValue()
    tertiary1_up_off = ycoff.SolutionValue() + SPILL_ycoff.SolutionValue()
    tertiary1_down = zc.SolutionValue() + SPILL_zc.SolutionValue()
    tertiary2_up_on = ydon.SolutionValue() + SPILL_ydon.SolutionValue()
    tertiary2_up_off = ydoff.SolutionValue() + SPILL_ydoff.SolutionValue()
    tertiary2_down = zd.SolutionValue() + SPILL_zd.SolutionValue()
    valeur = solver.Objective().Value()

    return([valeur,prod,primary_up_on,primary_up_off,primary_down,secondary_up_on,secondary_up_off
           ,secondary_down,tertiary1_up_on,tertiary1_up_off,tertiary1_down,tertiary2_up_on,tertiary2_up_off,tertiary2_down])



def repartition_sans_pmin(
    version : str,
    dictionnaire_valeur : dict[List[float]],
    t : int,
    ) -> List[int]:

    nbr_on_float = dictionnaire_valeur["nb_on"][t]
    nbr_on = floor(round(nbr_on_float,12))
    nbr_on_classic = ceil(round(nbr_on_float,12))

    
    p_min = dictionnaire_valeur["p_min"][t]
    min_generating = dictionnaire_valeur["min_generating"][t]

    if nbr_on * p_min < min_generating:
        return([nbr_on_classic])

    result = determination_generations_sans_pmin(nbr_on,dictionnaire_valeur,t)
    result_classic = determination_generations_sans_pmin(nbr_on_classic,dictionnaire_valeur,t)

    startup_cost = dictionnaire_valeur["startup_cost"][t]

    if (version == "perte" and result[0] + startup_cost < result_classic[0]) or (version == "sans" and result[0] < result_classic[0]) or (version == "gain" and result[0] < result_classic[0] + startup_cost):
        return[nbr_on]
    else :
        return[nbr_on_classic]
