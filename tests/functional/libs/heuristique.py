from pathlib import Path
from typing import Callable, List, Optional

from tests.functional.libs.heuristic_arrondi import *


def nouvel_appel_heuristique(
        fn_to_apply: Callable,
        ensemble_valeur : dict[List[float]],
        version: Optional[str] = None,
        option: Optional[str] = None,
) -> List[str]:
    
    parametres = ["nb_on","energy_generation","generation_reserve_up_primary_on","generation_reserve_up_primary_off",
                     "generation_reserve_down_primary","generation_reserve_up_secondary_on","generation_reserve_up_secondary_off",
                     "generation_reserve_down_secondary","generation_reserve_up_tertiary1_on","generation_reserve_up_tertiary1_off",
                     "generation_reserve_down_tertiary1","generation_reserve_up_tertiary2_on","generation_reserve_up_tertiary2_off",
                     "generation_reserve_down_tertiary2",
                     "p_max","p_min","nbr_max",
                     "participation_max_primary_reserve_up_on","participation_max_primary_reserve_up_off",
                     "participation_max_primary_reserve_down","participation_max_secondary_reserve_up_on",
                     "participation_max_secondary_reserve_up_off","participation_max_secondary_reserve_down",
                     "participation_max_tertiary1_reserve_up_on","participation_max_tertiary1_reserve_up_off",
                     "participation_max_tertiary1_reserve_down","participation_max_tertiary2_reserve_up_on",
                     "participation_max_tertiary2_reserve_up_off","participation_max_tertiary2_reserve_down",
                     "cost","startup_cost","fixed_cost",
                     "cost_participation_primary_reserve_up_on","cost_participation_primary_reserve_up_off","cost_participation_primary_reserve_down",
                     "cost_participation_secondary_reserve_up_on","cost_participation_secondary_reserve_up_off","cost_participation_secondary_reserve_down",
                     "cost_participation_tertiary1_reserve_up_on","cost_participation_tertiary1_reserve_up_off","cost_participation_tertiary1_reserve_down",
                     "cost_participation_tertiary2_reserve_up_on","cost_participation_tertiary2_reserve_up_off","cost_participation_tertiary2_reserve_down",
                     "spillage_cost","ens_cost","primary_reserve_up_not_supplied_cost","primary_reserve_down_not_supplied_cost",
                     "secondary_reserve_up_not_supplied_cost","secondary_reserve_down_not_supplied_cost",
                     "tertiary1_reserve_up_not_supplied_cost","tertiary1_reserve_down_not_supplied_cost",
                     "tertiary2_reserve_up_not_supplied_cost","tertiary2_reserve_down_not_supplied_cost",
                     "primary_reserve_up_oversupplied_cost","primary_reserve_down_oversupplied_cost",
                     "secondary_reserve_up_oversupplied_cost","secondary_reserve_down_oversupplied_cost",
                     "tertiary1_reserve_up_oversupplied_cost","tertiary1_reserve_down_oversupplied_cost",
                     "tertiary2_reserve_up_oversupplied_cost","tertiary2_reserve_down_oversupplied_cost"]
    valeur = [[] for t in range (168)]
    resultat = [ 0 for t in range(168)]
    for t in range(168):
        for i in range(len(parametres)):
            valeur[t].append(float(ensemble_valeur[parametres[i]][t]))
        resultat[t] = nouvel_old_heuristique(valeur[t])[0][0]
    return(resultat)    

        # if version is not None:
        #     if option is not None:
        #         result_heuristic = fn_to_apply(version, option, [i for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter))],
        #                                 [s for s in sol.values()], [p for p in param.values()])
        #     else:
        #         result_heuristic = fn_to_apply(version, [i for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter))],
        #                                 [s for s in sol.values()], [p for p in param.values()])
        # elif option is not None:
        #     result_heuristic = fn_to_apply(option, *[i for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter))],
        #                                 [s for s in sol.values()], [p for p in param.values()]) 
        # else:
        #     result_heuristic = fn_to_apply( [i for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter))],
        #                                 [s for s in sol.values()], [p for p in param.values()]) 

def nouvel_old_heuristique(
        variable: List[float],
    ) -> List[str]:
    
    arrondi_final = [old_arrondi(*[s for s in variable])]
    return arrondi_final

def old_heuristique(
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:
    
    arrondi_final = [old_arrondi(*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
    return arrondi_final


def heuristique_opti_repartition(
        version: str,
        option: str,
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:
    
    if version != "choix":
        arrondi_final = [ changement_arrondi(version,*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
        return arrondi_final

    arrondi_base = [ changement_arrondi("perte",*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
    arrondi_final = arrondi_base
    for t in range(1,len(horaire)-1):
        if arrondi_base[t-1] < arrondi_base[t] and arrondi_base[t] > arrondi_base[t+1]:
            arrondi_final[t] = changement_arrondi("gain",*[s[t] for s in variable],*[p[t] for p in params])        
        elif arrondi_base[t-1] < arrondi_base[t] or arrondi_base[t] > arrondi_base[t+1]:
            arrondi_final[t] = changement_arrondi("sans",*[s[t] for s in variable],*[p[t] for p in params])        
    return arrondi_final

 

def heuristique_opti_defaillance(
        version: str,
        horaire : List[str],
        variable: List[List[str]],
        params: List[List[str]],
    ) -> List[List[str]]:
    
    if version != "choix":
        arrondi_final = [ [arrondi_opti_defaillance(version,*[s[t] for s in variable],*[p[t] for p in params])[0]] for t in horaire]
        return arrondi_final

    resulat_perte = [ arrondi_opti_defaillance("perte",*[s[t] for s in variable],*[p[t] for p in params]) for t in range(horaire[0],horaire[len(horaire)-1])]
    resulat_perte.append(arrondi_opti_defaillance("sans",*[s[horaire[len(horaire)-1]] for s in variable],*[p[horaire[len(horaire)-1]] for p in params]))
    arrondi_base = [resulat_perte[t][0] for t in horaire]
    arrondi_min = [resulat_perte[t][1] for t in horaire]
    cout = [resulat_perte[t][2] for t in horaire]
    gain = [resulat_perte[t][3] for t in horaire]
    startup_cost = resulat_perte[horaire[0]][4]
    arrondi_final = [[resulat_perte[t][0]] for t in horaire]

    for t in range(horaire[1],len(horaire)-1):
        if arrondi_base[t-1] < arrondi_base[t] and arrondi_base[t] > arrondi_base[t+1]:
            cout_t = cout[t]
            gain_t = gain[t] + 2 * startup_cost
            if cout_t <= gain_t:
                arrondi_final[t] = [arrondi_min[t]]     
        elif arrondi_base[t-1] < arrondi_base[t] or arrondi_base[t] > arrondi_base[t+1]:
            cout_t = cout[t]
            gain_t = gain[t] + startup_cost
            if cout_t <= gain_t:
                arrondi_final[t] = [arrondi_min[t]]  

    if arrondi_base[horaire[0]] > arrondi_base[horaire[1]]:
        cout_0 = cout[horaire[0]]
        gain_0 = gain[horaire[0]] + 2 * startup_cost
        if cout_0 <= gain_0:
            arrondi_final[horaire[0]] = [arrondi_min[horaire[0]]]
    if arrondi_base[horaire[0]] == arrondi_base[horaire[1]]:
        cout_0 = cout[horaire[0]]
        gain_0 = gain[horaire[0]] + startup_cost
        if cout_0 <= gain_0:
            arrondi_final[horaire[0]] = [arrondi_min[horaire[0]]]
    
    return arrondi_final



def heuristique_eteint(
        version : str,
        option: str,
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:

    arrondi_final = [ arrondi_eteint(version, option,*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
    return arrondi_final




def heuristique_opti_entier(
        version : str,
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:

    
    if version != "choix":
        arrondi_final = [ [arrondi_opti_entier(version,*[s[t] for s in variable],*[p[t] for p in params])[0]] for t in horaire]
        return arrondi_final

    arrondi_base = [ arrondi_opti_entier("perte",*[s[t] for s in variable],*[p[t] for p in params]) for t in range(horaire[0],horaire[len(horaire)-1])]
    arrondi_base.append(arrondi_opti_entier("sans",*[s[horaire[len(horaire)-1]] for s in variable],*[p[horaire[len(horaire)-1]] for p in params]))
    arrondi_final = arrondi_base
    for t in range(horaire[1],len(horaire)-1):
        if arrondi_base[t-1] < arrondi_base[t] and arrondi_base[t] > arrondi_base[t+1]:
            arrondi_final[t] = arrondi_opti_entier("gain",*[s[t] for s in variable],*[p[t] for p in params])     
        elif arrondi_base[t-1] < arrondi_base[t] or arrondi_base[t] > arrondi_base[t+1]:
            arrondi_final[t] = arrondi_opti_entier("sans",*[s[t] for s in variable],*[p[t] for p in params])       
    if arrondi_base[horaire[0]] > arrondi_base[horaire[1]]:
        arrondi_final[horaire[0]] = [arrondi_opti_entier("sans",*[s[horaire[0]] for s in variable],*[p[horaire[0]] for p in params])]
    return arrondi_final

# def heuristique_mix(
#         horaire : List[str],
#         variable: List[List[str]],
#         params: Optional[List[List[str]]] = None,
#     ) -> List[List[str]]:

#     arrondi_base = [ arrondi_opti_sans_start_up(*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
#     arrondi_final = arrondi_base
#     for t in horaire:
#         if (((t - 1) in horaire and arrondi_base[t-1] >= arrondi_base[t])
#                              and ((t + 1) in horaire and arrondi_base[t+1] >= arrondi_base[t])):
#             arrondi_final[t] = arrondi_opti_avec_start_up(*[s[t] for s in variable],*[p[t] for p in params])        
#     return arrondi_final
