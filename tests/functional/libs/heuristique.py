from pathlib import Path
from typing import Callable, List, Optional



from tests.functional.libs.heuristic_arrondi import *

def old_heuristique(
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:
    
    arrondi_final = [ old_arrondi(*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
    return arrondi_final

def heuristique_optis_avec_start_up(
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:
    
    arrondi_final = [ arrondi_optis_avec_start_up(*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
    return arrondi_final

def heuristique_opti_avec_start_up(
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:
    
    arrondi_final = [ arrondi_opti_avec_start_up(*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
    return arrondi_final

def heuristique_opti_sans_start_up(
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:
    
    arrondi_final = [ arrondi_opti_sans_start_up(*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
    return arrondi_final

def nouvelle_heuristique(
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:
    
    arrondi_final = [ nouvelle_arrondi(*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
    return arrondi_final

def heuristique_mix(
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:

    arrondi_base = [ arrondi_opti_sans_start_up(*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
    arrondi_final = arrondi_base
    for t in horaire:
        if (((t - 1) in horaire and arrondi_base[t-1] >= arrondi_base[t])
                             and ((t + 1) in horaire and arrondi_base[t+1] >= arrondi_base[t])):
            arrondi_final[t] = arrondi_opti_avec_start_up(*[s[t] for s in variable],*[p[t] for p in params])        
    return arrondi_final

def old_heuristique_eteint(
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:

    arrondi_final = [ old_arrondi_eteint(*[s[t] for s in variable],*[p[t] for p in params]) for t in horaire]
    return arrondi_final

def changement_invisible(
        horaire : List[str],
        variable: List[List[str]],
        params: Optional[List[List[str]]] = None,
    ) -> List[List[str]]:

    a = [[variable[0][t]] for t in horaire]
    return(a)