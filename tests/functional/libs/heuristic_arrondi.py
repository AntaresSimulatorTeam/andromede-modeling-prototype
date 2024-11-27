from math import ceil,floor
from typing import Callable, List, Optional

from ortools.linear_solver import pywraplp
import ortools.linear_solver.pywraplp as lp
from ortools.sat.python import cp_model

def determination_generations(
    nbr_on : int,
    nbr_off_primary : int,
    nbr_off_secondary: int,
    nbr_off_tertiary1 : int,
    nbr_off_tertiary2 : int,
    energy_generation : float,
    generation_reserve_up_primary_on : float,
    generation_reserve_up_primary_off : float,
    generation_reserve_down_primary : float,
    generation_reserve_up_secondary_on : float,
    generation_reserve_up_secondary_off : float,
    generation_reserve_down_secondary : float,
    generation_reserve_up_tertiary1_on : float,
    generation_reserve_up_tertiary1_off : float,
    generation_reserve_down_tertiary1 : float,
    generation_reserve_up_tertiary2_on : float,
    generation_reserve_up_tertiary2_off : float,
    generation_reserve_down_tertiary2 : float,
    p_max : float,
    p_min : float,
    nb_units_max_invisible : float,
    participation_max_primary_reserve_up_on : float,
    participation_max_primary_reserve_up_off : float,
    participation_max_primary_reserve_down : float,
    participation_max_secondary_reserve_up_on : float,
    participation_max_secondary_reserve_up_off : float,
    participation_max_secondary_reserve_down : float,
    participation_max_tertiary1_reserve_up_on : float,
    participation_max_tertiary1_reserve_up_off : float,
    participation_max_tertiary1_reserve_down : float,
    participation_max_tertiary2_reserve_up_on : float,
    participation_max_tertiary2_reserve_up_off : float,
    participation_max_tertiary2_reserve_down : float,
    cost : float,
    fixed_cost : float,
    cost_participation_primary_reserve_up_on : float,
    cost_participation_primary_reserve_up_off : float,
    cost_participation_primary_reserve_down : float,
    cost_participation_secondary_reserve_up_on : float,
    cost_participation_secondary_reserve_up_off : float,
    cost_participation_secondary_reserve_down : float,
    cost_participation_tertiary1_reserve_up_on : float,
    cost_participation_tertiary1_reserve_up_off : float,
    cost_participation_tertiary1_reserve_down : float,
    cost_participation_tertiary2_reserve_up_on : float,   
    cost_participation_tertiary2_reserve_up_off : float,        
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
    primary_reserve_up_oversupplied_cost : float,
    primary_reserve_down_oversupplied_cost : float,
    secondary_reserve_up_oversupplied_cost : float,
    secondary_reserve_down_oversupplied_cost : float,
    tertiary1_reserve_up_oversupplied_cost : float,
    tertiary1_reserve_down_oversupplied_cost : float,
    tertiary2_reserve_up_oversupplied_cost : float,
    tertiary2_reserve_down_oversupplied_cost : float,
    ) -> List[float] :
        
    
    solver = lp.Solver.CreateSolver("SCIP")
        
    generation_reserve_up_primary = generation_reserve_up_primary_on + generation_reserve_up_primary_off
    generation_reserve_up_secondary = generation_reserve_up_secondary_on + generation_reserve_up_secondary_off
    generation_reserve_up_tertiary1 = generation_reserve_up_tertiary1_on + generation_reserve_up_tertiary1_off
    generation_reserve_up_tertiary2 = generation_reserve_up_tertiary2_on + generation_reserve_up_tertiary2_off

    x = solver.NumVar(0, min(energy_generation,nbr_on * p_max), "x") #Prod energie
    SPILL_x = solver.NumVar(0, nbr_on * p_max, "spillx")
    yaon = solver.NumVar(0, nbr_on * participation_max_primary_reserve_up_on, "yaon") #Prod_res+_on
    SPILL_yaon = solver.NumVar(0, nbr_on * p_max, "spillyaon")
    yaoff = solver.NumVar(0, nbr_off_primary * participation_max_primary_reserve_up_off, "yaoff") #Prod_res+_off
    SPILL_yaoff = solver.NumVar(0, nbr_off_primary * p_max, "spillyaoff")
    ybon = solver.NumVar(0, nbr_on * participation_max_secondary_reserve_up_on, "yaon") #Prod_res+_on
    SPILL_ybon = solver.NumVar(0, nbr_on * p_max, "spillybon")
    yboff = solver.NumVar(0, nbr_off_secondary * participation_max_secondary_reserve_up_off, "yaoff") #Prod_res+_on
    SPILL_yboff = solver.NumVar(0, nbr_off_secondary * p_max, "spillyboff")
    ycon = solver.NumVar(0, nbr_on * participation_max_tertiary1_reserve_up_on, "yaon") #Prod_res+_on
    SPILL_ycon = solver.NumVar(0, nbr_on * p_max, "spillycon")
    ycoff = solver.NumVar(0, nbr_off_tertiary1 * participation_max_tertiary1_reserve_up_off, "yaoff") #Prod_res+_off
    SPILL_ycoff = solver.NumVar(0, nbr_off_tertiary1 * p_max, "spillycoff")
    ydon = solver.NumVar(0, nbr_on * participation_max_tertiary2_reserve_up_on, "yaon") #Prod_res+_on
    SPILL_ydon = solver.NumVar(0, nbr_on * p_max, "spillydon")
    ydoff = solver.NumVar(0, nbr_off_tertiary2 * participation_max_tertiary2_reserve_up_off, "yaoff") #Prod_res+_off
    SPILL_ydoff = solver.NumVar(0, nbr_off_tertiary2 * p_max, "spillydoff")
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
    borne_min = nbr_on * p_min
    participation_max_primary_off = nbr_off_primary * participation_max_primary_reserve_up_off
    participation_max_secondary_off = nbr_off_secondary * participation_max_secondary_reserve_up_off
    participation_max_tertiary1_off = nbr_off_tertiary1 * participation_max_tertiary1_reserve_up_off
    participation_max_tertiary2_off = nbr_off_tertiary2 * participation_max_tertiary2_reserve_up_off
    participation_max_primary_on = nbr_on* participation_max_primary_reserve_up_on
    participation_max_secondary_on = nbr_on * participation_max_secondary_reserve_up_on
    participation_max_tertiary1_on = nbr_on * participation_max_tertiary1_reserve_up_on
    participation_max_tertiary2_on = nbr_on * participation_max_tertiary2_reserve_up_on
    participation_max_primary_down = nbr_on* participation_max_primary_reserve_down
    participation_max_secondary_down = nbr_on * participation_max_secondary_reserve_down
    participation_max_tertiary1_down = nbr_on * participation_max_tertiary1_reserve_down
    participation_max_tertiary2_down = nbr_on * participation_max_tertiary2_reserve_down
    borne_min_primary_off = nbr_off_primary * p_min
    borne_min_secondary_off = nbr_off_secondary * p_min
    borne_min_tertiary1_off = nbr_off_tertiary1 * p_min
    borne_min_tertiary2_off = nbr_off_tertiary2 * p_min
        
    solver.Add(1 * x + 1 * SPILL_x + 1 * yaon + 1 * SPILL_yaon + 1 * ybon + 1 * SPILL_ybon + 1 * ycon + 1 * SPILL_ycon + 1 * ydon + 1 * SPILL_ydon <= borne_max_on)
    solver.Add(1 * x + 1 * SPILL_x - 1 * za - 1 * SPILL_za - 1 * zb - 1 * SPILL_zb - 1 * zc - 1 * SPILL_zc - 1 * zd - 1 * SPILL_zd >= borne_min)
    solver.Add(1 * yaoff  + 1 * SPILL_yaoff + 1 * yboff  + 1 * SPILL_yaoff + 1 * ycoff  + 1 * SPILL_yaoff + 1 * ydoff  + 1 * SPILL_yaoff <= borne_max_off)
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
    solver.Add(1 * yaoff + 1 * SPILL_yaoff >= borne_min_primary_off)
    solver.Add(1 * yboff + 1 * SPILL_yboff >= borne_min_secondary_off)
    solver.Add(1 * ycoff + 1 * SPILL_ycoff >= borne_min_tertiary1_off)
    solver.Add(1 * ydoff + 1 * SPILL_ydoff >= borne_min_tertiary2_off)
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


def arrondi_eteint(
    version : str,
    option : str,
    energy_generation : float,
    generation_reserve_up_primary_on : float,
    generation_reserve_up_primary_off : float,
    generation_reserve_down_primary : float,
    generation_reserve_up_secondary_on : float,
    generation_reserve_up_secondary_off : float,
    generation_reserve_down_secondary : float,
    generation_reserve_up_tertiary1_on : float,
    generation_reserve_up_tertiary1_off : float,
    generation_reserve_down_tertiary1 : float,
    generation_reserve_up_tertiary2_on : float,
    generation_reserve_up_tertiary2_off : float,
    generation_reserve_down_tertiary2 : float,
    nbr_off_primary_float : float,
    nbr_off_secondary_float : float,
    nbr_off_tertiary1_float : float,
    nbr_off_tertiary2_float : float,
    nbr_on : int,
    p_max : float,
    p_min : float,
    nbr_units_max : int,
    participation_max_primary_reserve_up_on : float,
    participation_max_primary_reserve_up_off : float,
    participation_max_primary_reserve_down : float,
    participation_max_secondary_reserve_up_on : float,
    participation_max_secondary_reserve_up_off : float,
    participation_max_secondary_reserve_down : float,
    participation_max_tertiary1_reserve_up_on : float,
    participation_max_tertiary1_reserve_up_off : float,
    participation_max_tertiary1_reserve_down : float,
    participation_max_tertiary2_reserve_up_on : float,
    participation_max_tertiary2_reserve_up_off : float,
    participation_max_tertiary2_reserve_down : float,
    cost : float,
    fixed_cost : float,
    cost_participation_primary_reserve_up_on : float,
    cost_participation_primary_reserve_up_off : float,
    cost_participation_primary_reserve_down : float,
    cost_participation_secondary_reserve_up_on : float,
    cost_participation_secondary_reserve_up_off : float,
    cost_participation_secondary_reserve_down : float,
    cost_participation_tertiary1_reserve_up_on : float,
    cost_participation_tertiary1_reserve_up_off : float,
    cost_participation_tertiary1_reserve_down : float,
    cost_participation_tertiary2_reserve_up_on : float,   
    cost_participation_tertiary2_reserve_up_off : float,        
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
    primary_reserve_up_oversupplied_cost : float,
    primary_reserve_down_oversupplied_cost : float,
    secondary_reserve_up_oversupplied_cost : float,
    secondary_reserve_down_oversupplied_cost : float,
    tertiary1_reserve_up_oversupplied_cost : float,
    tertiary1_reserve_down_oversupplied_cost : float,
    tertiary2_reserve_up_oversupplied_cost : float,
    tertiary2_reserve_down_oversupplied_cost : float,
) -> List[int]:

    nbr_off_primary = min(ceil(round(nbr_off_primary_float,12)),nbr_units_max-nbr_on)
    nbr_off_secondary = min(ceil(round(nbr_off_secondary_float,12)),nbr_units_max-nbr_on)
    nbr_off_tertiary1 = min(ceil(round(nbr_off_tertiary1_float,12)),nbr_units_max-nbr_on)
    nbr_off_tertiary2 = min(ceil(round(nbr_off_tertiary2_float,12)),nbr_units_max-nbr_on)
    nbr_off_float = [nbr_off_primary_float,nbr_off_secondary_float,nbr_off_tertiary1_float,nbr_off_tertiary2_float]
    nbr_off = [nbr_off_primary,nbr_off_secondary,nbr_off_tertiary1,nbr_off_tertiary2]
    participation_max_off = [participation_max_primary_reserve_up_off,participation_max_secondary_reserve_up_off,participation_max_tertiary1_reserve_up_off,participation_max_tertiary2_reserve_up_off]
    cost_participation_off = [cost_participation_primary_reserve_up_off,cost_participation_secondary_reserve_up_off,cost_participation_tertiary1_reserve_up_off,cost_participation_tertiary2_reserve_up_off]
    cost_participation_on = [cost_participation_primary_reserve_up_on,cost_participation_secondary_reserve_up_on,cost_participation_tertiary1_reserve_up_on,cost_participation_tertiary2_reserve_up_on]
    cost_defaillance = [primary_reserve_up_not_supplied_cost,secondary_reserve_up_not_supplied_cost,tertiary1_reserve_up_not_supplied_cost,tertiary2_reserve_up_not_supplied_cost]

    if option == "taille":
        while sum(nbr_off) * p_min > p_max * (nbr_units_max - nbr_on):
            indice_maxi = 0
            excedent_maxi = min(nbr_off_primary_float-(nbr_off_primary-1),nbr_off_primary) * participation_max_primary_reserve_up_off
            for i in range(1,len(nbr_off)):
                if min(nbr_off_float[i]-(nbr_off[i]-1),nbr_off[i]) * participation_max_off[i] >= excedent_maxi:
                    indice_maxi = i
            nbr_off[indice_maxi] -= 1  

    if option == "cout_simple":
        while sum(nbr_off) * p_min > p_max * (nbr_units_max - nbr_on):
            indice_maxi = 0
            cout_maxi = cost_participation_primary_reserve_up_off * participation_max_primary_reserve_up_off * min(nbr_off_primary_float-(nbr_off_primary-1),nbr_off_primary)
            for i in range(1,len(nbr_off)):
                if cost_participation_off[i] * participation_max_off[i] * min(nbr_off_float[i]-(nbr_off[i]-1),nbr_off[i]) >= cout_maxi:
                    indice_maxi = i
            nbr_off[indice_maxi] -= 1

    if option == "difference_couts":
        while sum(nbr_off) * p_min > p_max * (nbr_units_max - nbr_on):
            indice_maxi = 0
            cout_maxi = (cost_participation_primary_reserve_up_off-cost_participation_primary_reserve_up_on) * participation_max_primary_reserve_up_off * min(nbr_off_primary_float-(nbr_off_primary-1),nbr_off_primary)
            for i in range(1,len(nbr_off)):
                if (cost_participation_off[i]-cost_participation_on[i]) * participation_max_off[i] * min(nbr_off_float[i]-(nbr_off[i]-1),nbr_off[i]) >= cout_maxi:
                    indice_maxi = i
            nbr_off[indice_maxi] -= 1

    if option == "cout_defaillance":
        while sum(nbr_off) * p_min > p_max * (nbr_units_max - nbr_on):
            premier_indice_non_nulle = 0
            while nbr_off[premier_indice_non_nulle] == 0 :
                premier_indice_non_nulle += 1
            cout_maxi = (cost_participation_off[premier_indice_non_nulle]-cost_defaillance[premier_indice_non_nulle]) * participation_max_off[premier_indice_non_nulle] * min(nbr_off_float[premier_indice_non_nulle]-(nbr_off[premier_indice_non_nulle]-1),nbr_off[premier_indice_non_nulle])
            indice_maxi = premier_indice_non_nulle
            for i in range(premier_indice_non_nulle+1,len(nbr_off)):
                if (nbr_off[i] != 0) and ((cost_participation_off[i]-cost_defaillance[i]) * participation_max_off[i] * min(nbr_off_float[i]-(nbr_off[i]-1),nbr_off[i]) >= cout_maxi):
                    indice_maxi = i
            nbr_off[indice_maxi] -= 1

    if option == "opti":
        
        model = cp_model.CpModel()
        

        x = model.new_int_var(0, nbr_off_primary, "nbr_primary")
        y = model.new_int_var(0, nbr_off_secondary, "nbr_secondary")
        z = model.new_int_var(0, nbr_off_tertiary1, "nbr_tertiary1")
        a = model.new_int_var(0, nbr_off_tertiary2, "nbr_tertiary2")

        borne_max = p_max * (nbr_units_max - nbr_on) 
        model.Add( p_min * x + p_min * y + p_min * z + p_min * a <= borne_max)

        model.maximize( determination_generations( nbr_on,
            x,
            y,
            z,
            a,
            energy_generation,
            generation_reserve_up_primary_on,
            generation_reserve_up_primary_off,
            generation_reserve_down_primary,
            generation_reserve_up_secondary_on,
            generation_reserve_up_secondary_off,
            generation_reserve_down_secondary,
            generation_reserve_up_tertiary1_on,
            generation_reserve_up_tertiary1_off,
            generation_reserve_down_tertiary1,
            generation_reserve_up_tertiary2_on,
            generation_reserve_up_tertiary2_off,
            generation_reserve_down_tertiary2,
            p_max,
            p_min,
            nbr_units_max,
            participation_max_primary_reserve_up_on,
            participation_max_primary_reserve_up_off,
            participation_max_primary_reserve_down,
            participation_max_secondary_reserve_up_on,
            participation_max_secondary_reserve_up_off,
            participation_max_secondary_reserve_down,
            participation_max_tertiary1_reserve_up_on,
            participation_max_tertiary1_reserve_up_off,
            participation_max_tertiary1_reserve_down,
            participation_max_tertiary2_reserve_up_on,
            participation_max_tertiary2_reserve_up_off,
            participation_max_tertiary2_reserve_down,
            cost,
            fixed_cost,
            cost_participation_primary_reserve_up_on,
            cost_participation_primary_reserve_up_off,
            cost_participation_primary_reserve_down,
            cost_participation_secondary_reserve_up_on,
            cost_participation_secondary_reserve_up_off,
            cost_participation_secondary_reserve_down,
            cost_participation_tertiary1_reserve_up_on,
            cost_participation_tertiary1_reserve_up_off,
            cost_participation_tertiary1_reserve_down,
            cost_participation_tertiary2_reserve_up_on,   
            cost_participation_tertiary2_reserve_up_off,        
            cost_participation_tertiary2_reserve_down,
            spillage_cost,
            ens_cost,
            primary_reserve_up_not_supplied_cost,
            primary_reserve_down_not_supplied_cost,
            secondary_reserve_up_not_supplied_cost,
            secondary_reserve_down_not_supplied_cost,
            tertiary1_reserve_up_not_supplied_cost,
            tertiary1_reserve_down_not_supplied_cost,
            tertiary2_reserve_up_not_supplied_cost,
            tertiary2_reserve_down_not_supplied_cost,
            primary_reserve_up_oversupplied_cost,
            primary_reserve_down_oversupplied_cost,
            secondary_reserve_up_oversupplied_cost,
            secondary_reserve_down_oversupplied_cost,
            tertiary1_reserve_up_oversupplied_cost,
            tertiary1_reserve_down_oversupplied_cost,
            tertiary2_reserve_up_oversupplied_cost,
            tertiary2_reserve_down_oversupplied_cost,
        ))

        solver = cp_model.CpSolver()
        status = solver.solve(model)
        
        nbr_off = [solver.value(x),solver.value(y),solver.value(z),solver.value(a)]

    if version == "reduction":
        result = determination_generations( nbr_on,
            nbr_off[0],
            nbr_off[1],
            nbr_off[2],
            nbr_off[3],
            energy_generation,
            generation_reserve_up_primary_on,
            generation_reserve_up_primary_off,
            generation_reserve_down_primary,
            generation_reserve_up_secondary_on,
            generation_reserve_up_secondary_off,
            generation_reserve_down_secondary,
            generation_reserve_up_tertiary1_on,
            generation_reserve_up_tertiary1_off,
            generation_reserve_down_tertiary1,
            generation_reserve_up_tertiary2_on,
            generation_reserve_up_tertiary2_off,
            generation_reserve_down_tertiary2,
            p_max,
            p_min,
            nbr_units_max,
            participation_max_primary_reserve_up_on,
            participation_max_primary_reserve_up_off,
            participation_max_primary_reserve_down,
            participation_max_secondary_reserve_up_on,
            participation_max_secondary_reserve_up_off,
            participation_max_secondary_reserve_down,
            participation_max_tertiary1_reserve_up_on,
            participation_max_tertiary1_reserve_up_off,
            participation_max_tertiary1_reserve_down,
            participation_max_tertiary2_reserve_up_on,
            participation_max_tertiary2_reserve_up_off,
            participation_max_tertiary2_reserve_down,
            cost,
            fixed_cost,
            cost_participation_primary_reserve_up_on,
            cost_participation_primary_reserve_up_off,
            cost_participation_primary_reserve_down,
            cost_participation_secondary_reserve_up_on,
            cost_participation_secondary_reserve_up_off,
            cost_participation_secondary_reserve_down,
            cost_participation_tertiary1_reserve_up_on,
            cost_participation_tertiary1_reserve_up_off,
            cost_participation_tertiary1_reserve_down,
            cost_participation_tertiary2_reserve_up_on,   
            cost_participation_tertiary2_reserve_up_off,        
            cost_participation_tertiary2_reserve_down,
            spillage_cost,
            ens_cost,
            primary_reserve_up_not_supplied_cost,
            primary_reserve_down_not_supplied_cost,
            secondary_reserve_up_not_supplied_cost,
            secondary_reserve_down_not_supplied_cost,
            tertiary1_reserve_up_not_supplied_cost,
            tertiary1_reserve_down_not_supplied_cost,
            tertiary2_reserve_up_not_supplied_cost,
            tertiary2_reserve_down_not_supplied_cost,
            primary_reserve_up_oversupplied_cost,
            primary_reserve_down_oversupplied_cost,
            secondary_reserve_up_oversupplied_cost,
            secondary_reserve_down_oversupplied_cost,
            tertiary1_reserve_up_oversupplied_cost,
            tertiary1_reserve_down_oversupplied_cost,
            tertiary2_reserve_up_oversupplied_cost,
            tertiary2_reserve_down_oversupplied_cost)
        result_changement = [result[0] + 1,result[0] + 1,result[0] + 1,result[0] + 1]
        for i in range(4):
            if nbr_off[i] > 0:
                nbr_off[i] -= 1
                result_changement[i] = determination_generations( nbr_on,
            nbr_off[0],
            nbr_off[1],
            nbr_off[2],
            nbr_off[3],
            energy_generation,
            generation_reserve_up_primary_on,
            generation_reserve_up_primary_off,
            generation_reserve_down_primary,
            generation_reserve_up_secondary_on,
            generation_reserve_up_secondary_off,
            generation_reserve_down_secondary,
            generation_reserve_up_tertiary1_on,
            generation_reserve_up_tertiary1_off,
            generation_reserve_down_tertiary1,
            generation_reserve_up_tertiary2_on,
            generation_reserve_up_tertiary2_off,
            generation_reserve_down_tertiary2,
            p_max,
            p_min,
            nbr_units_max,
            participation_max_primary_reserve_up_on,
            participation_max_primary_reserve_up_off,
            participation_max_primary_reserve_down,
            participation_max_secondary_reserve_up_on,
            participation_max_secondary_reserve_up_off,
            participation_max_secondary_reserve_down,
            participation_max_tertiary1_reserve_up_on,
            participation_max_tertiary1_reserve_up_off,
            participation_max_tertiary1_reserve_down,
            participation_max_tertiary2_reserve_up_on,
            participation_max_tertiary2_reserve_up_off,
            participation_max_tertiary2_reserve_down,
            cost,
            fixed_cost,
            cost_participation_primary_reserve_up_on,
            cost_participation_primary_reserve_up_off,
            cost_participation_primary_reserve_down,
            cost_participation_secondary_reserve_up_on,
            cost_participation_secondary_reserve_up_off,
            cost_participation_secondary_reserve_down,
            cost_participation_tertiary1_reserve_up_on,
            cost_participation_tertiary1_reserve_up_off,
            cost_participation_tertiary1_reserve_down,
            cost_participation_tertiary2_reserve_up_on,   
            cost_participation_tertiary2_reserve_up_off,        
            cost_participation_tertiary2_reserve_down,
            spillage_cost,
            ens_cost,
            primary_reserve_up_not_supplied_cost,
            primary_reserve_down_not_supplied_cost,
            secondary_reserve_up_not_supplied_cost,
            secondary_reserve_down_not_supplied_cost,
            tertiary1_reserve_up_not_supplied_cost,
            tertiary1_reserve_down_not_supplied_cost,
            tertiary2_reserve_up_not_supplied_cost,
            tertiary2_reserve_down_not_supplied_cost,
            primary_reserve_up_oversupplied_cost,
            primary_reserve_down_oversupplied_cost,
            secondary_reserve_up_oversupplied_cost,
            secondary_reserve_down_oversupplied_cost,
            tertiary1_reserve_up_oversupplied_cost,
            tertiary1_reserve_down_oversupplied_cost,
            tertiary2_reserve_up_oversupplied_cost,
            tertiary2_reserve_down_oversupplied_cost)[0]
                nbr_off[i] += 1
   
        while min(result_changement) < result[0]:
            mini = result[0]
            indice_mini = 0
            for i in range(4):
                if result_changement[i] < mini:
                    mini = result_changement[i]
                    indice_mini = i
            nbr_off[indice_mini] -= 1
            result[0] = mini
            for i in range(4):
                if nbr_off[i] > 0:
                    nbr_off[i] -= 1
                    result_changement[i] = determination_generations( nbr_on,
                nbr_off[0],
                nbr_off[1],
                nbr_off[2],
                nbr_off[3],
                energy_generation,
                generation_reserve_up_primary_on,
                generation_reserve_up_primary_off,
                generation_reserve_down_primary,
                generation_reserve_up_secondary_on,
                generation_reserve_up_secondary_off,
                generation_reserve_down_secondary,
                generation_reserve_up_tertiary1_on,
                generation_reserve_up_tertiary1_off,
                generation_reserve_down_tertiary1,
                generation_reserve_up_tertiary2_on,
                generation_reserve_up_tertiary2_off,
                generation_reserve_down_tertiary2,
                p_max,
                p_min,
                nbr_units_max,
                participation_max_primary_reserve_up_on,
                participation_max_primary_reserve_up_off,
                participation_max_primary_reserve_down,
                participation_max_secondary_reserve_up_on,
                participation_max_secondary_reserve_up_off,
                participation_max_secondary_reserve_down,
                participation_max_tertiary1_reserve_up_on,
                participation_max_tertiary1_reserve_up_off,
                participation_max_tertiary1_reserve_down,
                participation_max_tertiary2_reserve_up_on,
                participation_max_tertiary2_reserve_up_off,
                participation_max_tertiary2_reserve_down,
                cost,
                fixed_cost,
                cost_participation_primary_reserve_up_on,
                cost_participation_primary_reserve_up_off,
                cost_participation_primary_reserve_down,
                cost_participation_secondary_reserve_up_on,
                cost_participation_secondary_reserve_up_off,
                cost_participation_secondary_reserve_down,
                cost_participation_tertiary1_reserve_up_on,
                cost_participation_tertiary1_reserve_up_off,
                cost_participation_tertiary1_reserve_down,
                cost_participation_tertiary2_reserve_up_on,   
                cost_participation_tertiary2_reserve_up_off,        
                cost_participation_tertiary2_reserve_down,
                spillage_cost,
                ens_cost,
                primary_reserve_up_not_supplied_cost,
                primary_reserve_down_not_supplied_cost,
                secondary_reserve_up_not_supplied_cost,
                secondary_reserve_down_not_supplied_cost,
                tertiary1_reserve_up_not_supplied_cost,
                tertiary1_reserve_down_not_supplied_cost,
                tertiary2_reserve_up_not_supplied_cost,
                tertiary2_reserve_down_not_supplied_cost,
                primary_reserve_up_oversupplied_cost,
                primary_reserve_down_oversupplied_cost,
                secondary_reserve_up_oversupplied_cost,
                secondary_reserve_down_oversupplied_cost,
                tertiary1_reserve_up_oversupplied_cost,
                tertiary1_reserve_down_oversupplied_cost,
                tertiary2_reserve_up_oversupplied_cost,
                tertiary2_reserve_down_oversupplied_cost)[0]
                    nbr_off[i] += 1

    return nbr_off


def arrondi_opti_repartition(
    version : str,
    option : str,
    nbr_on_float : float,
    energy_generation : float,
    generation_reserve_up_primary_on : float,
    generation_reserve_up_primary_off : float,
    generation_reserve_down_primary : float,
    generation_reserve_up_secondary_on : float,
    generation_reserve_up_secondary_off : float,
    generation_reserve_down_secondary : float,
    generation_reserve_up_tertiary1_on : float,
    generation_reserve_up_tertiary1_off : float,
    generation_reserve_down_tertiary1 : float,
    generation_reserve_up_tertiary2_on : float,
    generation_reserve_up_tertiary2_off : float,
    generation_reserve_down_tertiary2 : float,
    nbr_off_primary_float : float,
    nbr_off_secondary_float : float,
    nbr_off_tertiary1_float : float,
    nbr_off_tertiary2_float : float,
    p_max : float,
    p_min : float,
    nb_units_max_invisible : float,
    participation_max_primary_reserve_up_on : float,
    participation_max_primary_reserve_up_off : float,
    participation_max_primary_reserve_down : float,
    participation_max_secondary_reserve_up_on : float,
    participation_max_secondary_reserve_up_off : float,
    participation_max_secondary_reserve_down : float,
    participation_max_tertiary1_reserve_up_on : float,
    participation_max_tertiary1_reserve_up_off : float,
    participation_max_tertiary1_reserve_down : float,
    participation_max_tertiary2_reserve_up_on : float,
    participation_max_tertiary2_reserve_up_off : float,
    participation_max_tertiary2_reserve_down : float,
    cost : float,
    startup_cost : float,
    fixed_cost : float,
    cost_participation_primary_reserve_up_on : float,
    cost_participation_primary_reserve_up_off : float,
    cost_participation_primary_reserve_down : float,
    cost_participation_secondary_reserve_up_on : float,
    cost_participation_secondary_reserve_up_off : float,
    cost_participation_secondary_reserve_down : float,
    cost_participation_tertiary1_reserve_up_on : float,
    cost_participation_tertiary1_reserve_up_off : float,
    cost_participation_tertiary1_reserve_down : float,
    cost_participation_tertiary2_reserve_up_on : float,   
    cost_participation_tertiary2_reserve_up_off : float,        
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
    primary_reserve_up_oversupplied_cost : float,
    primary_reserve_down_oversupplied_cost : float,
    secondary_reserve_up_oversupplied_cost : float,
    secondary_reserve_down_oversupplied_cost : float,
    tertiary1_reserve_up_oversupplied_cost : float,
    tertiary1_reserve_down_oversupplied_cost : float,
    tertiary2_reserve_up_oversupplied_cost : float,
    tertiary2_reserve_down_oversupplied_cost : float,
) -> List[int]:
    

    nbr_on = floor(round(nbr_on_float,12))
    [nbr_off_primary,nbr_off_secondary,nbr_off_tertiary1,nbr_off_tertiary2]  = arrondi_eteint(
        " ",
        option,
        energy_generation,
        generation_reserve_up_primary_on,
        generation_reserve_up_primary_off,
        generation_reserve_down_primary,
        generation_reserve_up_secondary_on,
        generation_reserve_up_secondary_off,
        generation_reserve_down_secondary,
        generation_reserve_up_tertiary1_on,
        generation_reserve_up_tertiary1_off,
        generation_reserve_down_tertiary1,
        generation_reserve_up_tertiary2_on,
        generation_reserve_up_tertiary2_off,
        generation_reserve_down_tertiary2,
        nbr_off_primary_float,
        nbr_off_secondary_float,
        nbr_off_tertiary1_float,
        nbr_off_tertiary2_float,
        nbr_on,
        p_max,
        p_min,
        nb_units_max_invisible,
        participation_max_primary_reserve_up_on,
        participation_max_primary_reserve_up_off,
        participation_max_primary_reserve_down,
        participation_max_secondary_reserve_up_on,
        participation_max_secondary_reserve_up_off,
        participation_max_secondary_reserve_down,
        participation_max_tertiary1_reserve_up_on,
        participation_max_tertiary1_reserve_up_off,
        participation_max_tertiary1_reserve_down,
        participation_max_tertiary2_reserve_up_on,
        participation_max_tertiary2_reserve_up_off,
        participation_max_tertiary2_reserve_down,
        cost,
        fixed_cost,
        cost_participation_primary_reserve_up_on,
        cost_participation_primary_reserve_up_off,
        cost_participation_primary_reserve_down,
        cost_participation_secondary_reserve_up_on,
        cost_participation_secondary_reserve_up_off,
        cost_participation_secondary_reserve_down,
        cost_participation_tertiary1_reserve_up_on,
        cost_participation_tertiary1_reserve_up_off,
        cost_participation_tertiary1_reserve_down,
        cost_participation_tertiary2_reserve_up_on,   
        cost_participation_tertiary2_reserve_up_off,        
        cost_participation_tertiary2_reserve_down,
        spillage_cost,
        ens_cost,
        primary_reserve_up_not_supplied_cost,
        primary_reserve_down_not_supplied_cost,
        secondary_reserve_up_not_supplied_cost,
        secondary_reserve_down_not_supplied_cost,
        tertiary1_reserve_up_not_supplied_cost,
        tertiary1_reserve_down_not_supplied_cost,
        tertiary2_reserve_up_not_supplied_cost,
        tertiary2_reserve_down_not_supplied_cost,
        primary_reserve_up_oversupplied_cost,
        primary_reserve_down_oversupplied_cost,
        secondary_reserve_up_oversupplied_cost,
        secondary_reserve_down_oversupplied_cost,
        tertiary1_reserve_up_oversupplied_cost,
        tertiary1_reserve_down_oversupplied_cost,
        tertiary2_reserve_up_oversupplied_cost,
        tertiary2_reserve_down_oversupplied_cost,  
        )
 

    nbr_on_classic = ceil(round(nbr_on_float,12))
    [nbr_off_primary_classic,nbr_off_secondary_classic,nbr_off_tertiary1_classic,nbr_off_tertiary2_classic]  = arrondi_eteint(
        " ",
        option,
        energy_generation,
        generation_reserve_up_primary_on,
        generation_reserve_up_primary_off,
        generation_reserve_down_primary,
        generation_reserve_up_secondary_on,
        generation_reserve_up_secondary_off,
        generation_reserve_down_secondary,
        generation_reserve_up_tertiary1_on,
        generation_reserve_up_tertiary1_off,
        generation_reserve_down_tertiary1,
        generation_reserve_up_tertiary2_on,
        generation_reserve_up_tertiary2_off,
        generation_reserve_down_tertiary2,
        nbr_off_primary_float,
        nbr_off_secondary_float,
        nbr_off_tertiary1_float,
        nbr_off_tertiary2_float,
        nbr_on_classic,
        p_max,
        p_min,
        nb_units_max_invisible,
        participation_max_primary_reserve_up_on,
        participation_max_primary_reserve_up_off,
        participation_max_primary_reserve_down,
        participation_max_secondary_reserve_up_on,
        participation_max_secondary_reserve_up_off,
        participation_max_secondary_reserve_down,
        participation_max_tertiary1_reserve_up_on,
        participation_max_tertiary1_reserve_up_off,
        participation_max_tertiary1_reserve_down,
        participation_max_tertiary2_reserve_up_on,
        participation_max_tertiary2_reserve_up_off,
        participation_max_tertiary2_reserve_down,
        cost,
        fixed_cost,
        cost_participation_primary_reserve_up_on,
        cost_participation_primary_reserve_up_off,
        cost_participation_primary_reserve_down,
        cost_participation_secondary_reserve_up_on,
        cost_participation_secondary_reserve_up_off,
        cost_participation_secondary_reserve_down,
        cost_participation_tertiary1_reserve_up_on,
        cost_participation_tertiary1_reserve_up_off,
        cost_participation_tertiary1_reserve_down,
        cost_participation_tertiary2_reserve_up_on,   
        cost_participation_tertiary2_reserve_up_off,        
        cost_participation_tertiary2_reserve_down,
        spillage_cost,
        ens_cost,
        primary_reserve_up_not_supplied_cost,
        primary_reserve_down_not_supplied_cost,
        secondary_reserve_up_not_supplied_cost,
        secondary_reserve_down_not_supplied_cost,
        tertiary1_reserve_up_not_supplied_cost,
        tertiary1_reserve_down_not_supplied_cost,
        tertiary2_reserve_up_not_supplied_cost,
        tertiary2_reserve_down_not_supplied_cost,
        primary_reserve_up_oversupplied_cost,
        primary_reserve_down_oversupplied_cost,
        secondary_reserve_up_oversupplied_cost,
        secondary_reserve_down_oversupplied_cost,
        tertiary1_reserve_up_oversupplied_cost,
        tertiary1_reserve_down_oversupplied_cost,
        tertiary2_reserve_up_oversupplied_cost,
        tertiary2_reserve_down_oversupplied_cost,  
        )
 



    result = determination_generations(
        nbr_on,
        nbr_off_primary,
        nbr_off_secondary,
        nbr_off_tertiary1,
        nbr_off_tertiary2,
        energy_generation,
        generation_reserve_up_primary_on,
        generation_reserve_up_primary_off,
        generation_reserve_down_primary,
        generation_reserve_up_secondary_on,
        generation_reserve_up_secondary_off,
        generation_reserve_down_secondary,
        generation_reserve_up_tertiary1_on,
        generation_reserve_up_tertiary1_off,
        generation_reserve_down_tertiary1,
        generation_reserve_up_tertiary2_on,
        generation_reserve_up_tertiary2_off,
        generation_reserve_down_tertiary2,
        p_max,
        p_min,
        nb_units_max_invisible,
        participation_max_primary_reserve_up_on,
        participation_max_primary_reserve_up_off,
        participation_max_primary_reserve_down,
        participation_max_secondary_reserve_up_on,
        participation_max_secondary_reserve_up_off,
        participation_max_secondary_reserve_down,
        participation_max_tertiary1_reserve_up_on,
        participation_max_tertiary1_reserve_up_off,
        participation_max_tertiary1_reserve_down,
        participation_max_tertiary2_reserve_up_on,
        participation_max_tertiary2_reserve_up_off,
        participation_max_tertiary2_reserve_down,
        cost,
        fixed_cost,
        cost_participation_primary_reserve_up_on,
        cost_participation_primary_reserve_up_off,
        cost_participation_primary_reserve_down,
        cost_participation_secondary_reserve_up_on,
        cost_participation_secondary_reserve_up_off,
        cost_participation_secondary_reserve_down,
        cost_participation_tertiary1_reserve_up_on,
        cost_participation_tertiary1_reserve_up_off,
        cost_participation_tertiary1_reserve_down,
        cost_participation_tertiary2_reserve_up_on,   
        cost_participation_tertiary2_reserve_up_off,        
        cost_participation_tertiary2_reserve_down,
        spillage_cost,
        ens_cost,
        primary_reserve_up_not_supplied_cost,
        primary_reserve_down_not_supplied_cost,
        secondary_reserve_up_not_supplied_cost,
        secondary_reserve_down_not_supplied_cost,
        tertiary1_reserve_up_not_supplied_cost,
        tertiary1_reserve_down_not_supplied_cost,
        tertiary2_reserve_up_not_supplied_cost,
        tertiary2_reserve_down_not_supplied_cost,
        primary_reserve_up_oversupplied_cost,
        primary_reserve_down_oversupplied_cost,
        secondary_reserve_up_oversupplied_cost,
        secondary_reserve_down_oversupplied_cost,
        tertiary1_reserve_up_oversupplied_cost,
        tertiary1_reserve_down_oversupplied_cost,
        tertiary2_reserve_up_oversupplied_cost,
        tertiary2_reserve_down_oversupplied_cost,
        )
    result_classic = determination_generations(
        nbr_on_classic,
        nbr_off_primary_classic,
        nbr_off_secondary_classic,
        nbr_off_tertiary1_classic,
        nbr_off_tertiary2_classic,
        energy_generation,
        generation_reserve_up_primary_on,
        generation_reserve_up_primary_off,
        generation_reserve_down_primary,
        generation_reserve_up_secondary_on,
        generation_reserve_up_secondary_off,
        generation_reserve_down_secondary,
        generation_reserve_up_tertiary1_on,
        generation_reserve_up_tertiary1_off,
        generation_reserve_down_tertiary1,
        generation_reserve_up_tertiary2_on,
        generation_reserve_up_tertiary2_off,
        generation_reserve_down_tertiary2,
        p_max,
        p_min,
        nb_units_max_invisible,
        participation_max_primary_reserve_up_on,
        participation_max_primary_reserve_up_off,
        participation_max_primary_reserve_down,
        participation_max_secondary_reserve_up_on,
        participation_max_secondary_reserve_up_off,
        participation_max_secondary_reserve_down,
        participation_max_tertiary1_reserve_up_on,
        participation_max_tertiary1_reserve_up_off,
        participation_max_tertiary1_reserve_down,
        participation_max_tertiary2_reserve_up_on,
        participation_max_tertiary2_reserve_up_off,
        participation_max_tertiary2_reserve_down,
        cost,
        fixed_cost,
        cost_participation_primary_reserve_up_on,
        cost_participation_primary_reserve_up_off,
        cost_participation_primary_reserve_down,
        cost_participation_secondary_reserve_up_on,
        cost_participation_secondary_reserve_up_off,
        cost_participation_secondary_reserve_down,
        cost_participation_tertiary1_reserve_up_on,
        cost_participation_tertiary1_reserve_up_off,
        cost_participation_tertiary1_reserve_down,
        cost_participation_tertiary2_reserve_up_on,   
        cost_participation_tertiary2_reserve_up_off,        
        cost_participation_tertiary2_reserve_down,
        spillage_cost,
        ens_cost,
        primary_reserve_up_not_supplied_cost,
        primary_reserve_down_not_supplied_cost,
        secondary_reserve_up_not_supplied_cost,
        secondary_reserve_down_not_supplied_cost,
        tertiary1_reserve_up_not_supplied_cost,
        tertiary1_reserve_down_not_supplied_cost,
        tertiary2_reserve_up_not_supplied_cost,
        tertiary2_reserve_down_not_supplied_cost,
        primary_reserve_up_oversupplied_cost,
        primary_reserve_down_oversupplied_cost,
        secondary_reserve_up_oversupplied_cost,
        secondary_reserve_down_oversupplied_cost,
        tertiary1_reserve_up_oversupplied_cost,
        tertiary1_reserve_down_oversupplied_cost,
        tertiary2_reserve_up_oversupplied_cost,
        tertiary2_reserve_down_oversupplied_cost,
        )
    
    if (version == "perte" and result[0] + startup_cost < result_classic[0]) or (version == "sans" and result[0] < result_classic[0]) or (version == "gain" and result[0] < result_classic[0] + startup_cost):
        nbr_on_final = nbr_on
    else :
        nbr_on_final = nbr_on_classic



    
    # generation_reserve_up_primary = generation_reserve_up_primary_off + generation_reserve_up_primary_on
    # generation_reserve_up_secondary = generation_reserve_up_secondary_off + generation_reserve_up_secondary_on
    # generation_reserve_up_tertiary1 = generation_reserve_up_tertiary1_off + generation_reserve_up_tertiary1_on
    # generation_reserve_up_tertiary2 = generation_reserve_up_tertiary2_off + generation_reserve_up_tertiary2_on

    # if cost_participation_primary_reserve_up_off < cost_participation_primary_reserve_up_on:
    #     besoin_reserve_primary_off = min(generation_reserve_up_primary_on+generation_reserve_up_primary_off,participation_max_primary_reserve_up_off*nbr_off_primary_final)
    # else:
    #     besoin_reserve_primary_off = max(min(generation_reserve_up_primary_on+generation_reserve_up_primary_off-min(participation_max_primary_reserve_up_on*nbr_on_final,p_max*nbr_on_final-energy_generation)
    #                                     ,participation_max_primary_reserve_up_off*nbr_off_primary_final),0)
    # if max(besoin_reserve_primary_off,p_min)*cost_participation_primary_reserve_up_off > primary_reserve_up_not_supplied_cost * besoin_reserve_primary_off:
    #     nbr_off_primary_final = 0
    
    return [nbr_on_final]



#    nbr_off_final = [nbr_off_primary_final,nbr_off_secondary_final,nbr_off_tertiary1_final,nbr_off_tertiary2_final]
#     result_changement = [result_final[0] + 1,result_final[0] + 1,result_final[0] + 1,result_final[0] + 1]
#     for i in range(4):
#             if nbr_off_final[i] > 0:
#                 nbr_off_final[i] -= 1
#                 result_changement[i] = determination_generations(nbr_on_final,nbr_off_final[0],nbr_off_final[1],nbr_off_final[2],nbr_off_final[3])[0]
#                 nbr_off_final[i] += 1
    
#     while min(result_changement) < result_final[0]:
#         mini = result_final[0]
#         indice_mini = 0
#         for i in range(4):
#             if result_changement[i] < mini:
#                 mini = result_changement[i]
#                 indice_mini = i
#         nbr_off_final[indice_mini] -= 1
#         result_final[0] = mini
#         for i in range(4):
#             if nbr_off_final[i] > 0:
#                 nbr_off_final[i] -= 1
#                 result_changement[i] = determination_generations(nbr_on_final,nbr_off_final[0],nbr_off_final[1],nbr_off_final[2],nbr_off_final[3])[0]
#                 nbr_off_final[i] += 1
     


def arrondi_opti_defaillance(
    version : str,
    nbr_on_float : float,
    energy_generation : float,
    generation_reserve_up_primary_on : float,
    generation_reserve_up_primary_off : float,
    generation_reserve_down_primary : float,
    generation_reserve_up_secondary_on : float,
    generation_reserve_up_secondary_off : float,
    generation_reserve_down_secondary : float,
    generation_reserve_up_tertiary1_on : float,
    generation_reserve_up_tertiary1_off : float,
    generation_reserve_down_tertiary1 : float,
    generation_reserve_up_tertiary2_on : float,
    generation_reserve_up_tertiary2_off : float,
    generation_reserve_down_tertiary2 : float,
    nbr_off_primary_float : float,
    nbr_off_secondary_float : float,
    nbr_off_tertiary1_float : float,
    nbr_off_tertiary2_float : float,
    p_max : float,
    p_min : float,
    nb_units_max_invisible : float,
    participation_max_primary_reserve_up_on : float,
    participation_max_primary_reserve_up_off : float,
    participation_max_primary_reserve_down : float,
    participation_max_secondary_reserve_up_on : float,
    participation_max_secondary_reserve_up_off : float,
    participation_max_secondary_reserve_down : float,
    participation_max_tertiary1_reserve_up_on : float,
    participation_max_tertiary1_reserve_up_off : float,
    participation_max_tertiary1_reserve_down : float,
    participation_max_tertiary2_reserve_up_on : float,
    participation_max_tertiary2_reserve_up_off : float,
    participation_max_tertiary2_reserve_down : float,
    cost : float,
    startup_cost : float,
    fixed_cost : float,
    cost_participation_primary_reserve_up_on : float,
    cost_participation_primary_reserve_up_off : float,
    cost_participation_primary_reserve_down : float,
    cost_participation_secondary_reserve_up_on : float,
    cost_participation_secondary_reserve_up_off : float,
    cost_participation_secondary_reserve_down : float,
    cost_participation_tertiary1_reserve_up_on : float,
    cost_participation_tertiary1_reserve_up_off : float,
    cost_participation_tertiary1_reserve_down : float,
    cost_participation_tertiary2_reserve_up_on : float,   
    cost_participation_tertiary2_reserve_up_off : float,        
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
    primary_reserve_up_oversupplied_cost : float,
    primary_reserve_down_oversupplied_cost : float,
    secondary_reserve_up_oversupplied_cost : float,
    secondary_reserve_down_oversupplied_cost : float,
    tertiary1_reserve_up_oversupplied_cost : float,
    tertiary1_reserve_down_oversupplied_cost : float,
    tertiary2_reserve_up_oversupplied_cost : float,
    tertiary2_reserve_down_oversupplied_cost : float,
) -> List[int]:
    
    nbr_on = floor(round(nbr_on_float,12))
    nbr_on_classic = ceil(round(nbr_on_float,12))

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

    borne_max = max(0,generation_reserve_up + energy_generation - nbr_on * p_max)
    borne_min = energy_generation - generation_reserve_down - nbr_on*p_min
    
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
        return [nbr_on,cout,gain,startup_cost]
    return [nbr_on_classic,cout,gain,startup_cost]


def old_arrondi(
    nbr_on_float : float,
    energy_generation : Optional[float] = 0,
    generation_reserve_up_primary_on : Optional[float] = 0,
    generation_reserve_up_primary_off : Optional[float] = 0,
    generation_reserve_down_primary : Optional[float] = 0,
    generation_reserve_up_secondary_on : Optional[float] = 0,
    generation_reserve_up_secondary_off : Optional[float] = 0,
    generation_reserve_down_secondary : Optional[float] = 0,
    generation_reserve_up_tertiary1_on : Optional[float] = 0,
    generation_reserve_up_tertiary1_off : Optional[float] = 0,
    generation_reserve_down_tertiary1 : Optional[float] = 0,
    generation_reserve_up_tertiary2_on : Optional[float] = 0,
    generation_reserve_up_tertiary2_off : Optional[float] = 0,
    generation_reserve_down_tertiary2 : Optional[float] = 0,
    nbr_off_primary_float : Optional[float] = 0,
    nbr_off_secondary_float : Optional[float] = 0,
    nbr_off_tertiary1_float : Optional[float] = 0,
    nbr_off_tertiary2_float : Optional[float] = 0,
    p_max : Optional[float] = 0,
    p_min : Optional[float] = 0,
    nb_units_max_invisible : Optional[float] = 0,
    participation_max_primary_reserve_up_on : Optional[float] = 0,
    participation_max_primary_reserve_up_off : Optional[float] = 0,
    participation_max_primary_reserve_down : Optional[float] = 0,
    participation_max_secondary_reserve_up_on : Optional[float] = 0,
    participation_max_secondary_reserve_up_off : Optional[float] = 0,
    participation_max_secondary_reserve_down : Optional[float] = 0,
    participation_max_tertiary1_reserve_up_on : Optional[float] = 0,
    participation_max_tertiary1_reserve_up_off : Optional[float] = 0,
    participation_max_tertiary1_reserve_down : Optional[float] = 0,
    participation_max_tertiary2_reserve_up_on : Optional[float] = 0,
    participation_max_tertiary2_reserve_up_off : Optional[float] = 0,
    participation_max_tertiary2_reserve_down : Optional[float] = 0,
    cost : Optional[float] = 0,
    startup_cost : Optional[float] = 0,
    fixed_cost : Optional[float] = 0,
    cost_participation_primary_reserve_up_on : Optional[float] = 0,
    cost_participation_primary_reserve_up_off : Optional[float] = 0,
    cost_participation_primary_reserve_down : Optional[float] = 0,
    cost_participation_secondary_reserve_up_on : Optional[float] = 0,
    cost_participation_secondary_reserve_up_off : Optional[float] = 0,
    cost_participation_secondary_reserve_down : Optional[float] = 0,
    cost_participation_tertiary1_reserve_up_on : Optional[float] = 0,
    cost_participation_tertiary1_reserve_up_off : Optional[float] = 0,
    cost_participation_tertiary1_reserve_down : Optional[float] = 0,
    cost_participation_tertiary2_reserve_up_on : Optional[float] = 0,   
    cost_participation_tertiary2_reserve_up_off : Optional[float] = 0,       
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
    primary_reserve_up_oversupplied_cost : Optional[float] = 0,
    primary_reserve_down_oversupplied_cost : Optional[float] = 0,
    secondary_reserve_up_oversupplied_cost : Optional[float] = 0,
    secondary_reserve_down_oversupplied_cost : Optional[float] = 0,
    tertiary1_reserve_up_oversupplied_cost : Optional[float] = 0,
    tertiary1_reserve_down_oversupplied_cost : Optional[float] = 0,
    tertiary2_reserve_up_oversupplied_cost : Optional[float] = 0,
    tertiary2_reserve_down_oversupplied_cost : Optional[float] = 0,
) -> List[int]:
    
    nbr_on = ceil(round(nbr_on_float,12))
    return[nbr_on]





# def arrondi_opti_avec_start_up(
#     nbr_on_float : float,
#     energy_generation : float,
#     generation_reserve_up_primary_on : float,
#     generation_reserve_up_primary_off : float,
#     generation_reserve_down_primary : float,
#     generation_reserve_up_secondary_on : float,
#     generation_reserve_up_secondary_off : float,
#     generation_reserve_down_secondary : float,
#     generation_reserve_up_tertiary1_on : float,
#     generation_reserve_up_tertiary1_off : float,
#     generation_reserve_down_tertiary1 : float,
#     generation_reserve_up_tertiary2_on : float,
#     generation_reserve_up_tertiary2_off : float,
#     generation_reserve_down_tertiary2 : float,
#     nbr_off_primary_float : float,
#     nbr_off_secondary_float : float,
#     nbr_off_tertiary1_float : float,
#     nbr_off_tertiary2_float : float,
#     p_max : float,
#     p_min : float,
#     nb_units_max_invisible : float,
#     participation_max_primary_reserve_up_on : float,
#     participation_max_primary_reserve_up_off : float,
#     participation_max_primary_reserve_down : float,
#     participation_max_secondary_reserve_up_on : float,
#     participation_max_secondary_reserve_up_off : float,
#     participation_max_secondary_reserve_down : float,
#     participation_max_tertiary1_reserve_up_on : float,
#     participation_max_tertiary1_reserve_up_off : float,
#     participation_max_tertiary1_reserve_down : float,
#     participation_max_tertiary2_reserve_up_on : float,
#     participation_max_tertiary2_reserve_up_off : float,
#     participation_max_tertiary2_reserve_down : float,
#     cost : float,
#     startup_cost : float,
#     fixed_cost : float,
#     cost_participation_primary_reserve_up_on : float,
#     cost_participation_primary_reserve_up_off : float,
#     cost_participation_primary_reserve_down : float,
#     cost_participation_secondary_reserve_up_on : float,
#     cost_participation_secondary_reserve_up_off : float,
#     cost_participation_secondary_reserve_down : float,
#     cost_participation_tertiary1_reserve_up_on : float,
#     cost_participation_tertiary1_reserve_up_off : float,
#     cost_participation_tertiary1_reserve_down : float,
#     cost_participation_tertiary2_reserve_up_on : float,   
#     cost_participation_tertiary2_reserve_up_off : float,        
#     cost_participation_tertiary2_reserve_down : float,
#     spillage_cost : float,
#     ens_cost : float,
#     primary_reserve_up_not_supplied_cost : float,
#     primary_reserve_down_not_supplied_cost : float,
#     secondary_reserve_up_not_supplied_cost : float,
#     secondary_reserve_down_not_supplied_cost : float,
#     tertiary1_reserve_up_not_supplied_cost : float,
#     tertiary1_reserve_down_not_supplied_cost : float,
#     tertiary2_reserve_up_not_supplied_cost : float,
#     tertiary2_reserve_down_not_supplied_cost : float,
#     primary_reserve_up_oversupplied_cost : float,
#     primary_reserve_down_oversupplied_cost : float,
#     secondary_reserve_up_oversupplied_cost : float,
#     secondary_reserve_down_oversupplied_cost : float,
#     tertiary1_reserve_up_oversupplied_cost : float,
#     tertiary1_reserve_down_oversupplied_cost : float,
#     tertiary2_reserve_up_oversupplied_cost : float,
#     tertiary2_reserve_down_oversupplied_cost : float,
# ) -> List[int]:
    

#     nbr_on = floor(round(nbr_on_float,12))
#     nbr_on_classic = ceil(round(nbr_on_float,12))

   
#     solver = lp.Solver.CreateSolver("SCIP")


#     # UNSP_primary_up_on_min = max(0,generation_reserve_up_primary_on-nbr_on*participation_max_primary_reserve_up_on) 
#     # SPILL_primary_up_off_max = nbr_off_primary_classic*participation_max_primary_reserve_up_off - generation_reserve_up_primary_off
    
    

#     x = solver.NumVar(0, min(energy_generation,nbr_on * p_max), "x") #Prod energie
#     ya = solver.NumVar(0, min(generation_reserve_up_primary_on,nbr_on * participation_max_primary_reserve_up_on), "ya") #Prod_res+_on
#     za = solver.NumVar(0, min(generation_reserve_down_primary,nbr_on * participation_max_primary_reserve_down), "za")    #Prod_res-
#     yb = solver.NumVar(0, min(generation_reserve_up_secondary_on,nbr_on * participation_max_secondary_reserve_up_on), "yb") #Prod_res+
#     zb = solver.NumVar(0, min(generation_reserve_down_secondary,nbr_on * participation_max_secondary_reserve_down), "zb")    #Prod_res-
#     yc = solver.NumVar(0, min(generation_reserve_up_tertiary1_on,nbr_on * participation_max_tertiary1_reserve_up_on), "yc") #Prod_res+
#     zc = solver.NumVar(0, min(generation_reserve_down_tertiary1,nbr_on * participation_max_tertiary1_reserve_down), "zc")    #Prod_res-
#     yd = solver.NumVar(0, min(generation_reserve_up_tertiary2_on,nbr_on * participation_max_tertiary2_reserve_up_on), "yd") #Prod_res+
#     zd = solver.NumVar(0, min(generation_reserve_down_tertiary2,nbr_on * participation_max_tertiary2_reserve_down), "zd")    #Prod_res-

#     borne_max = nbr_on * p_max
#     borne_min = nbr_on * p_min
    
#     solver.Add(1 * x + 1 * ya + 1 * yb + 1 * yc + 1 * yd <= borne_max)
#     solver.Add(1 * x - 1 * za - 1 * zb - 1 * zc - 1 * zd >= borne_min)


#     solver.Minimize(cost_participation_primary_reserve_up_on * ya
#                     + primary_reserve_up_not_supplied_cost * (generation_reserve_up_primary_on - ya)
#                      + cost_participation_secondary_reserve_up_on * yb
#                      + secondary_reserve_up_not_supplied_cost * (generation_reserve_up_secondary_on - yb)
#                       + cost_participation_tertiary1_reserve_up_on * yc
#                       + tertiary1_reserve_up_not_supplied_cost * (generation_reserve_up_tertiary1_on - yc)
#                        + cost_participation_tertiary2_reserve_up_on * yd
#                        + tertiary2_reserve_up_not_supplied_cost * (generation_reserve_up_tertiary2_on - yd)
#                         + cost_participation_primary_reserve_down * za
#                         + primary_reserve_down_not_supplied_cost * (generation_reserve_down_primary - za)
#                          + cost_participation_secondary_reserve_down * zb
#                          + secondary_reserve_down_not_supplied_cost * (generation_reserve_down_secondary - zb)
#                           + cost_participation_tertiary1_reserve_down * zc
#                           + tertiary1_reserve_down_not_supplied_cost * (generation_reserve_down_tertiary1 - zc)
#                            + cost_participation_tertiary2_reserve_down * zd
#                            + tertiary2_reserve_down_not_supplied_cost * (generation_reserve_down_tertiary2 - zd)
#                             + cost * x
#                             + ens_cost * (energy_generation - x))

#     # Solve the system.
#     status = solver.Solve()

#     generation_reserve_up_on = generation_reserve_up_primary_on + generation_reserve_up_secondary_on + generation_reserve_up_tertiary1_on + generation_reserve_up_tertiary2_on
#     generation_reserve_down = generation_reserve_down_primary + generation_reserve_down_secondary + generation_reserve_down_tertiary1 + generation_reserve_down_tertiary2

#     energy_generation_classique = max(nbr_on_classic * p_min + generation_reserve_down, min(energy_generation,nbr_on_classic * p_max - generation_reserve_up_on))

#     gain = fixed_cost - startup_cost + (cost * energy_generation_classique 
#                           + cost_participation_primary_reserve_up_on * generation_reserve_up_primary_on
#                           + cost_participation_primary_reserve_down * generation_reserve_down_primary
#                           + cost_participation_secondary_reserve_up_on * generation_reserve_up_secondary_on + cost_participation_secondary_reserve_down * generation_reserve_down_secondary
#                           + cost_participation_tertiary1_reserve_up_on * generation_reserve_up_tertiary1_on + cost_participation_tertiary1_reserve_down * generation_reserve_down_tertiary1
#                           + cost_participation_tertiary2_reserve_up_on * generation_reserve_up_tertiary2_on + cost_participation_tertiary2_reserve_down * generation_reserve_down_tertiary2
#                           ) 
    

#     prod = x.SolutionValue()
#     primary_up_on = ya.SolutionValue()
#     primary_down = za.SolutionValue()
#     secondary_up = yb.SolutionValue()
#     secondary_down = zb.SolutionValue()
#     tertiary1_up = yc.SolutionValue()
#     tertiary1_down = zc.SolutionValue()
#     tertiary2_up = yd.SolutionValue()
#     tertiary2_down = zd.SolutionValue()
#     valeur = solver.Objective().Value()

#     new_energy_generation = prod

#     if solver.Objective().Value() < gain:  
#         nbr_on_final = nbr_on
#         energy_generation = new_energy_generation
#     else : 
#         nbr_on_final = nbr_on_classic
#         energy_generation = energy_generation_classique
#     if nbr_on + nbr_off_primary_float > nb_units_max_invisible:
#         nbr_off_primary_final = floor(round(nbr_off_primary_float,12))
#     else :
#         nbr_off_primary_final = ceil(round(nbr_off_primary_float,12))
    
#     if cost_participation_primary_reserve_up_off < cost_participation_primary_reserve_up_on:
#         besoin_reserve_primary_off = min(generation_reserve_up_primary_on+generation_reserve_up_primary_off,participation_max_primary_reserve_up_off*nbr_off_primary_final)
#     else:
#         besoin_reserve_primary_off = max(min(generation_reserve_up_primary_on+generation_reserve_up_primary_off-min(participation_max_primary_reserve_up_on*nbr_on_final,p_max*nbr_on_final-energy_generation)
#                                         ,participation_max_primary_reserve_up_off*nbr_off_primary_final),0)
#     # if max(besoin_reserve_primary_off,p_min)*cost_participation_primary_reserve_up_off > primary_reserve_up_not_supplied_cost * besoin_reserve_primary_off:
#     #     nbr_off_primary_final = 0
    
#     return [nbr_on_final,nbr_off_primary_final,nbr_off_secondary_float,nbr_off_tertiary1_float,nbr_off_tertiary2_float]



# def arrondi_opti_defaillance_sans_start_up(
#     nbr_on_float : float,
#     energy_generation : float,
#     generation_reserve_up_primary : float,
#     generation_reserve_down_primary : float,
#     generation_reserve_up_secondary : float,
#     generation_reserve_down_secondary : float,
#     generation_reserve_up_tertiary1 : float,
#     generation_reserve_down_tertiary1 : float,
#     generation_reserve_up_tertiary2 : float,
#     generation_reserve_down_tertiary2 : float,
#     p_max : float,
#     p_min : float,
#     participation_max_primary_reserve_up : float,
#     participation_max_primary_reserve_down : float,
#     participation_max_secondary_reserve_up : float,
#     participation_max_secondary_reserve_down : float,
#     participation_max_tertiary1_reserve_up : float,
#     participation_max_tertiary1_reserve_down : float,
#     participation_max_tertiary2_reserve_up : float,
#     participation_max_tertiary2_reserve_down : float,
#     cost : float,
#     startup_cost : float,
#     fixed_cost : float,
#     cost_participation_primary_reserve_up : float,
#     cost_participation_primary_reserve_down : float,
#     cost_participation_secondary_reserve_up : float,
#     cost_participation_secondary_reserve_down : float,
#     cost_participation_tertiary1_reserve_up : float,
#     cost_participation_tertiary1_reserve_down : float,
#     cost_participation_tertiary2_reserve_up : float,         
#     cost_participation_tertiary2_reserve_down : float,
#     spillage_cost : float,
#     ens_cost : float,
#     primary_reserve_up_not_supplied_cost : float,
#     primary_reserve_down_not_supplied_cost : float,
#     secondary_reserve_up_not_supplied_cost : float,
#     secondary_reserve_down_not_supplied_cost : float,
#     tertiary1_reserve_up_not_supplied_cost : float,
#     tertiary1_reserve_down_not_supplied_cost : float,
#     tertiary2_reserve_up_not_supplied_cost : float,
#     tertiary2_reserve_down_not_supplied_cost : float,
# ) -> List[int]:
    
#     nbr_on = floor(round(nbr_on_float,12))
#     nbr_on_classic = ceil(round(nbr_on_float,12))

#     solver = lp.Solver.CreateSolver("SCIP")

#     UNSP_primary_up_min = max(0,generation_reserve_up_primary-nbr_on*participation_max_primary_reserve_up)  
#     UNSP_primary_down_min = max(0,generation_reserve_down_primary-nbr_on*participation_max_primary_reserve_down)
#     UNSP_secondary_up_min = max(0,generation_reserve_up_secondary-nbr_on*participation_max_secondary_reserve_up)  
#     UNSP_secondary_down_min = max(0,generation_reserve_down_secondary-nbr_on*participation_max_secondary_reserve_down)
#     UNSP_tertiary1_up_min = max(0,generation_reserve_up_tertiary1-nbr_on*participation_max_tertiary1_reserve_up)  
#     UNSP_tertiary1_down_min = max(0,generation_reserve_down_tertiary1-nbr_on*participation_max_tertiary1_reserve_down)
#     UNSP_tertiary2_up_min = max(0,generation_reserve_up_tertiary2-nbr_on*participation_max_tertiary2_reserve_up)  
#     UNSP_tertiary2_down_min = max(0,generation_reserve_down_tertiary2-nbr_on*participation_max_tertiary2_reserve_down)

#     x = solver.NumVar(0, energy_generation, "x") #UNSP_prod
#     ya = solver.NumVar(UNSP_primary_up_min, generation_reserve_up_primary, "ya") #UNSP_res+
#     za = solver.NumVar(UNSP_primary_down_min, generation_reserve_down_primary, "za")    #UNSP_res-
#     yb = solver.NumVar(UNSP_secondary_up_min, generation_reserve_up_secondary, "yb") #UNSP_res+
#     zb = solver.NumVar(UNSP_secondary_down_min, generation_reserve_down_secondary, "zb")    #UNSP_res-
#     yc = solver.NumVar(UNSP_tertiary1_up_min, generation_reserve_up_tertiary1, "yc") #UNSP_res+
#     zc = solver.NumVar(UNSP_tertiary1_down_min, generation_reserve_down_tertiary1, "zc")    #UNSP_res-
#     yd = solver.NumVar(UNSP_tertiary2_up_min, generation_reserve_up_tertiary2, "yd") #UNSP_res+
#     zd = solver.NumVar(UNSP_tertiary2_down_min, generation_reserve_down_tertiary2, "zd")    #UNSP_res-

#     generation_reserve_up = generation_reserve_up_primary + generation_reserve_up_secondary + generation_reserve_up_tertiary1 + generation_reserve_up_tertiary2
#     generation_reserve_down = generation_reserve_down_primary + generation_reserve_down_secondary + generation_reserve_down_tertiary1 + generation_reserve_down_tertiary2

#     borne_max = max(0,generation_reserve_up + energy_generation - nbr_on * p_max)
#     borne_min = energy_generation - generation_reserve_down - nbr_on*p_min
    
#     solver.Add(1 * x + 1 * ya + 1 * yb + 1 * yc + 1 * yd >= borne_max)
#     solver.Add(1 * x - 1 * za - 1 * zb - 1 * zc - 1 * zd <= borne_min)


#     solver.Minimize((primary_reserve_up_not_supplied_cost-cost_participation_primary_reserve_up) * ya
#                      + (secondary_reserve_up_not_supplied_cost-cost_participation_secondary_reserve_up) * yb
#                       + (tertiary1_reserve_up_not_supplied_cost-cost_participation_tertiary1_reserve_up) * yc
#                        + (tertiary2_reserve_up_not_supplied_cost-cost_participation_tertiary2_reserve_up) * yd
#                         + (primary_reserve_down_not_supplied_cost-cost_participation_primary_reserve_down) * za
#                          + (secondary_reserve_down_not_supplied_cost-cost_participation_secondary_reserve_down) * zb
#                           + (tertiary1_reserve_down_not_supplied_cost-cost_participation_tertiary1_reserve_down) * zc 
#                            + (tertiary2_reserve_down_not_supplied_cost-cost_participation_tertiary2_reserve_down) * zd
#                             + (ens_cost - cost) * x)

#     # Solve the system.
#     status = solver.Solve()

#     a = x.SolutionValue()
#     b = ya.SolutionValue()
#     c = za.SolutionValue()
#     d = solver.Objective().Value()

#     # if nbr_on_float > 12 and p_max > 600:
#     #     e = f,
#     #     g = e

#     energy_generation_classique = max(nbr_on_classic * p_min + generation_reserve_down,
#                                       min(energy_generation,
#                                           nbr_on_classic * p_max - generation_reserve_up))
#     gain = fixed_cost  + (cost + spillage_cost) * (energy_generation_classique - energy_generation)
#     if solver.Objective().Value() <= gain:  
#         return [nbr_on]
#     return [nbr_on_classic]

# def nouvelle_arrondi(
#     nbr_on_float : float,
#     energy_generation : float,
#     generation_reserve_up_primary : float,
#     generation_reserve_down_primary : float,
#     generation_reserve_up_secondary : float,
#     generation_reserve_down_secondary : float,
#     generation_reserve_up_tertiary1 : float,
#     generation_reserve_down_tertiary1 : float,
#     generation_reserve_up_tertiary2 : float,
#     generation_reserve_down_tertiary2 : float,
#     p_max : float,
#     p_min : float,
#     participation_max_primary_reserve_up : float,
#     participation_max_primary_reserve_down : float,
#     participation_max_secondary_reserve_up : float,
#     participation_max_secondary_reserve_down : float,
#     participation_max_tertiary1_reserve_up : float,
#     participation_max_tertiary1_reserve_down : float,
#     participation_max_tertiary2_reserve_up : float,
#     participation_max_tertiary2_reserve_down : float,
#     cost : float,
#     startup_cost : float,
#     fixed_cost : float,
#     cost_participation_primary_reserve_up_on : float,
#     cost_participation_primary_reserve_up_off : float,
#     cost_participation_primary_reserve_down : float,
#     cost_participation_secondary_reserve_up_on : float,
#     cost_participation_secondary_reserve_up_off : float,
#     cost_participation_secondary_reserve_down : float,
#     cost_participation_tertiary1_reserve_up_on : float,
#     cost_participation_tertiary1_reserve_up_off : float,
#     cost_participation_tertiary1_reserve_down : float,
#     cost_participation_tertiary2_reserve_up_on : float,   
#     cost_participation_tertiary2_reserve_up_off : float,        
#     cost_participation_tertiary2_reserve_down : float,
#     spillage_cost : float,
#     ens_cost : float,
#     primary_reserve_up_not_supplied_cost : float,
#     primary_reserve_down_not_supplied_cost : float,
#     secondary_reserve_up_not_supplied_cost : float,
#     secondary_reserve_down_not_supplied_cost : float,
#     tertiary1_reserve_up_not_supplied_cost : float,
#     tertiary1_reserve_down_not_supplied_cost : float,
#     tertiary2_reserve_up_not_supplied_cost : float,
#     tertiary2_reserve_down_not_supplied_cost : float,
# ) -> List[int]:
    
#     nbr_on = floor(round(nbr_on_float,12))
#     nbr_on_classic = ceil(round(nbr_on_float,12))

#     UNSP_primary_up = max(0,generation_reserve_up_primary-nbr_on*participation_max_primary_reserve_up)
#     UNSP_primary_down = max(0,generation_reserve_down_primary-nbr_on*participation_max_primary_reserve_down)
#     UNSP_secondary_up = max(0,generation_reserve_up_secondary-nbr_on*participation_max_secondary_reserve_up)
#     UNSP_secondary_down = max(0,generation_reserve_down_secondary-nbr_on*participation_max_secondary_reserve_down)
#     UNSP_tertiary1_up = max(0,generation_reserve_up_tertiary1-nbr_on*participation_max_tertiary1_reserve_up)
#     UNSP_tertiary1_down = max(0,generation_reserve_down_tertiary1-nbr_on*participation_max_tertiary1_reserve_down)
#     UNSP_tertiary2_up = max(0,generation_reserve_up_tertiary2-nbr_on*participation_max_tertiary2_reserve_up)
#     UNSP_tertiary2_down = max(0,generation_reserve_down_tertiary2-nbr_on*participation_max_tertiary2_reserve_down)
    
#     generation_reserve_up = generation_reserve_up_primary + generation_reserve_up_secondary + generation_reserve_up_tertiary1 + generation_reserve_up_tertiary2
#     generation_reserve_down = generation_reserve_down_primary + generation_reserve_down_secondary + generation_reserve_down_tertiary1 + generation_reserve_down_tertiary2

#     UNSP_prod = max(0,energy_generation+generation_reserve_up-nbr_on*p_max)-UNSP_primary_up-UNSP_secondary_up-UNSP_tertiary1_up-UNSP_tertiary2_up
    
#     cout = primary_reserve_up_not_supplied_cost*UNSP_primary_up + primary_reserve_down_not_supplied_cost*UNSP_primary_down+ secondary_reserve_up_not_supplied_cost*UNSP_secondary_up + secondary_reserve_down_not_supplied_cost*UNSP_secondary_down+ tertiary1_reserve_up_not_supplied_cost*UNSP_tertiary1_up + tertiary1_reserve_down_not_supplied_cost*UNSP_tertiary1_down+tertiary2_reserve_up_not_supplied_cost*UNSP_tertiary2_up + tertiary2_reserve_down_not_supplied_cost*UNSP_tertiary2_down+ (ens_cost-(cost+spillage_cost))*UNSP_prod
    

#     energy_generation_classique = max(nbr_on_classic * p_min + generation_reserve_down,
#                                       min(energy_generation,
#                                           nbr_on_classic * p_max - generation_reserve_up))
#     gain = fixed_cost  + (cost + spillage_cost) * ( energy_generation_classique - energy_generation) - startup_cost
#     if cout < gain:
#         return[nbr_on]
#     return[nbr_on_classic]
 
