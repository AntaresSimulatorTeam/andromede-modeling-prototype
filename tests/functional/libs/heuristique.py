from pathlib import Path
from typing import Callable, List, Optional

from tests.functional.libs.heuristic_arrondi_indep import *
from tests.functional.libs.heuristic_arrondi_sans_pmin import *
from tests.functional.libs.heuristic_arrondi_mutualise import *


def old_heuristique(
        horaire : List[int],
        dictionnaire_valeur: dict[List[float]],
    ) -> List[List[int]]:
    
    arrondi_final = [old_arrondi(dictionnaire_valeur,t) for t in horaire]
    return arrondi_final


def heuristique_opti_defaillance(
        horaire : List[int],
        dictionnaire_valeur: dict[List[float]],
        version: str,
    ) -> List[List[int]]:
    
    if version != "choix":
        arrondi_final = [[defaillance(version,dictionnaire_valeur,t)[0]] for t in horaire]
        return arrondi_final

    resulat_perte = [defaillance("perte",dictionnaire_valeur,t) for t in range(horaire[0],horaire[len(horaire)-1])]
    resulat_perte.append(defaillance("sans",dictionnaire_valeur,len(horaire)-1))
    arrondi_base = [resulat_perte[t][0] for t in horaire]
    arrondi_min = [resulat_perte[t][1] for t in horaire]
    cout = [resulat_perte[t][2] for t in horaire]
    gain = [resulat_perte[t][3] for t in horaire]
    startup_cost = resulat_perte[horaire[0]][4]
    arrondi_final = [[arrondi_base[t]] for t in horaire]

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



def heuristique_opti_repartition_sans_pmin(
        horaire : List[int],
        dictionnaire_valeur: dict[List[float]],
        version: str,
    ) -> List[List[int]]:


    if version != "choix":
        arrondi_final = [[repartition_sans_pmin(version,dictionnaire_valeur,t)[0]] for t in horaire]
        return arrondi_final

    resulat_perte = [repartition_sans_pmin("perte",dictionnaire_valeur,t) for t in range(horaire[0],horaire[len(horaire)-1])]
    resulat_perte.append(repartition_sans_pmin("sans",dictionnaire_valeur,len(horaire)-1))
    arrondi_base = [resulat_perte[t][0] for t in horaire]
    arrondi_min = [resulat_perte[t][1] for t in horaire]
    cout_baisse = [resulat_perte[t][2] for t in horaire]
    cout_hausse = [resulat_perte[t][3] for t in horaire]
    startup_cost = resulat_perte[horaire[0]][4]
    arrondi_final = [[arrondi_base[t]] for t in horaire]

    for t in range(horaire[1],len(horaire)-1):
        if arrondi_base[t-1] < arrondi_base[t] and arrondi_base[t] > arrondi_base[t+1]:
            if cout_baisse[t] < cout_hausse[t] + startup_cost:
                arrondi_final[t] = [arrondi_min[t]]     
        elif arrondi_base[t-1] < arrondi_base[t] or arrondi_base[t] > arrondi_base[t+1]:
            if cout_baisse[t] < cout_hausse[t]:
                arrondi_final[t] = [arrondi_min[t]]  

    if arrondi_base[horaire[0]] > arrondi_base[horaire[1]]:
        if cout_baisse[0] < cout_hausse[0] + startup_cost:
            arrondi_final[horaire[0]] = [arrondi_min[horaire[0]]]
    if arrondi_base[horaire[0]] == arrondi_base[horaire[1]]:
        if cout_baisse[0] < cout_hausse[0]:
            arrondi_final[horaire[0]] = [arrondi_min[horaire[0]]]
    
    return arrondi_final


    # if version != "choix":
    #     arrondi_final = [ repartition_sans_pmin(version,dictionnaire_valeur,t)  for t in horaire]
    #     return arrondi_final

    # arrondi_base = [ repartition_sans_pmin("perte",dictionnaire_valeur,t)  for t in horaire]
    # arrondi_final = arrondi_base
    # for t in range(1,len(horaire)-1):
    #     if arrondi_base[t-1] < arrondi_base[t] and arrondi_base[t] > arrondi_base[t+1]:
    #         arrondi_final[t] = repartition_sans_pmin("gain",dictionnaire_valeur,t)        
    #     elif arrondi_base[t-1] < arrondi_base[t] or arrondi_base[t] > arrondi_base[t+1]:
    #         arrondi_final[t] = repartition_sans_pmin("sans",dictionnaire_valeur,t)        
    # return arrondi_final

 
def heuristique_opti_repartition_indep(
        horaire : List[int],
        dictionnaire_valeur: dict[List[float]],
        version: str,
        option : str,
        bonus : str,
    ) -> List[List[int]]:
    
    if version != "choix":
        arrondi_final = [ repartition_indep(version,option,bonus,dictionnaire_valeur,t) for t in horaire]
        return arrondi_final

    arrondi_base = [ repartition_indep("perte",option,bonus,dictionnaire_valeur,t) for t in horaire]
    arrondi_final = arrondi_base
    for t in range(1,len(horaire)-1):
        if arrondi_base[t-1] < arrondi_base[t] and arrondi_base[t] > arrondi_base[t+1]:
            arrondi_final[t] = repartition_indep("gain",option,bonus,dictionnaire_valeur,t)        
        elif arrondi_base[t-1] < arrondi_base[t] or arrondi_base[t] > arrondi_base[t+1]:
            arrondi_final[t] = repartition_indep("sans",option,bonus,dictionnaire_valeur,t)        
    return arrondi_final



def heuristique_opti_repartition_mutualise(
        horaire : List[int],
        dictionnaire_valeur: dict[List[float]],
        version: str,
        option : str,
        bonus : str,
    ) -> List[List[int]]:


    if version != "choix":
        arrondi_final = [[repartition_mutualise(version,option,bonus,dictionnaire_valeur,t)[0]] for t in horaire]
        return arrondi_final

    resulat_perte = [repartition_mutualise("perte",option,bonus,dictionnaire_valeur,t) for t in range(horaire[0],horaire[len(horaire)-1])]
    resulat_perte.append(repartition_mutualise("sans",option,bonus,dictionnaire_valeur,len(horaire)-1))
    arrondi_base = [resulat_perte[t][0] for t in horaire]
    arrondi_min = [resulat_perte[t][1] for t in horaire]
    cout_baisse = [resulat_perte[t][2] for t in horaire]
    cout_hausse = [resulat_perte[t][3] for t in horaire]
    startup_cost = resulat_perte[horaire[0]][4]
    arrondi_final = [[arrondi_base[t]] for t in horaire]

    for t in range(horaire[1],len(horaire)-1):
        if arrondi_base[t-1] < arrondi_base[t] and arrondi_base[t] > arrondi_base[t+1]:
            if cout_baisse[t] < cout_hausse[t] + startup_cost:
                arrondi_final[t] = [arrondi_min[t]]     
        elif arrondi_base[t-1] < arrondi_base[t] or arrondi_base[t] > arrondi_base[t+1]:
            if cout_baisse[t] < cout_hausse[t]:
                arrondi_final[t] = [arrondi_min[t]]  

    if arrondi_base[horaire[0]] > arrondi_base[horaire[1]]:
        if cout_baisse[0] < cout_hausse[0] + startup_cost:
            arrondi_final[horaire[0]] = [arrondi_min[horaire[0]]]
    if arrondi_base[horaire[0]] == arrondi_base[horaire[1]]:
        if cout_baisse[0] < cout_hausse[0]:
            arrondi_final[horaire[0]] = [arrondi_min[horaire[0]]]
    
    return arrondi_final


def heuristique_eteint_mutualise(
        horaire : List[int],
        dictionnaire_valeur: dict[List[float]],
        nbr_on : List[int],
        option : str,
        bonus : str,
    ) -> List[List[int]]:

    arrondi_final = [ arrondi_eteint_mutualise(bonus, option, nbr_on[t], dictionnaire_valeur,t) for t in horaire]
    return arrondi_final

def heuristique_eteint_indep(
        horaire : List[int],
        dictionnaire_valeur: dict[List[float]],
        option : str,
        bonus: str,
    ) -> List[List[int]]:

    arrondi_final = [ arrondi_eteint_indep(bonus, option, dictionnaire_valeur["nb_units_max"][t], dictionnaire_valeur,t) for t in horaire]
    return arrondi_final

def heuristique_opti_entier_indep(
        horaire : List[int],
        dictionnaire_valeur: dict[List[float]],
        version: str,
    ) -> List[List[int]]:

    
    if version != "choix":
        arrondi_final = [ [arrondi_opti_entier_indep(version,dictionnaire_valeur,t)] for t in horaire]
        return arrondi_final

    arrondi_base = [ arrondi_opti_entier_indep("perte",dictionnaire_valeur,t) for t in range(horaire[0],horaire[len(horaire)-1])]
    arrondi_base.append(arrondi_opti_entier_indep("sans",dictionnaire_valeur,t))
    arrondi_final = arrondi_base
    for t in range(horaire[1],len(horaire)-1):
        if arrondi_base[t-1] < arrondi_base[t] and arrondi_base[t] > arrondi_base[t+1]:
            arrondi_final[t] = arrondi_opti_entier_indep("gain",dictionnaire_valeur,t)     
        elif arrondi_base[t-1] < arrondi_base[t] or arrondi_base[t] > arrondi_base[t+1]:
            arrondi_final[t] = arrondi_opti_entier_indep("sans",dictionnaire_valeur,t)  
    if arrondi_base[horaire[0]] > arrondi_base[horaire[1]]:
        arrondi_final[horaire[0]] = [arrondi_opti_entier_indep("sans",dictionnaire_valeur,t)]
    return arrondi_final
