from pathlib import Path
from typing import Callable, List, Optional

from tests.functional.libs.heuristic_arrondi import *


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
        arrondi_final = [ arrondi_opti_repartition(version,option,*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
        return arrondi_final

    arrondi_base = [ arrondi_opti_repartition("perte",option,*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
    arrondi_final = arrondi_base
    for t in range(1,len(horaire)-1):
        if arrondi_base[t-1] < arrondi_base[t] and arrondi_base[t] > arrondi_base[t+1]:
            arrondi_final[t] = arrondi_opti_repartition("gain",option,*[s[t] for s in variable],*[p[t] for p in params])        
        elif arrondi_base[t-1] < arrondi_base[t] or arrondi_base[t] > arrondi_base[t+1]:
            arrondi_final[t] = arrondi_opti_repartition("sans",option,*[s[t] for s in variable],*[p[t] for p in params])        
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
