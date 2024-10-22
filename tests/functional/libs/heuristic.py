from math import ceil,floor


def nouvelle_heuristique(
    nbr_on_float : float,
    energy_generation : float,
    generation_reserve_up : float,
    generation_reserve_down : float,
    p_max : float,
    p_min : float,
    participation_max_primary_reserve_up : float,
    participation_max_primary_reserve_down : float,
    cost : float,
    startup_cost : float,
    fixed_cost : float,
) -> int:
    
    nbr_on = floor(round(nbr_on_float,12))
    nbr_on_classic = ceil(round(nbr_on_float,12))
    UNSP_up = max(0,generation_reserve_up-nbr_on*participation_max_primary_reserve_up)
    UNSP_down = max(0,generation_reserve_down-nbr_on*participation_max_primary_reserve_down)
    UNSP_prod = max(0,energy_generation+generation_reserve_up-nbr_on*p_max)-UNSP_up
    cout = 1000*(UNSP_up+UNSP_down)+ (100-cost)*UNSP_prod
    energy_generation_classique = max(nbr_on_classic * p_min + generation_reserve_down,
                                      min(energy_generation,
                                          nbr_on_classic * p_max - generation_reserve_up))
    gain = fixed_cost  + cost * ( energy_generation_classique - energy_generation)
    if cout < gain:
        return(nbr_on)
    return(nbr_on_classic)
