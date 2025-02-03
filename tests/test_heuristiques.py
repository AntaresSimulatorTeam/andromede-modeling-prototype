from tests.functional.libs.heuristique import *

def test_heuristiques():
    ensemble_valeurs = {}

    ensemble_valeurs["energy_generation"] = [205.551812335205]
    ensemble_valeurs["nb_on"] = [2.03433661056286]
    ensemble_valeurs["p_max"] = [148.7]
    ensemble_valeurs["ens_cost"] = [4000]
    ensemble_valeurs["p_min"] = [41.0412]
    ensemble_valeurs["cost"] = [130.982]
    ensemble_valeurs["startup_cost"] = [3420.1]
    ensemble_valeurs["fixed_cost"] = [0]
    ensemble_valeurs["primary_reserve_up_not_supplied_cost"] = [5000]
    ensemble_valeurs["primary_reserve_up_oversupplied_cost"] = [5]
    ensemble_valeurs["primary_reserve_down_not_supplied_cost"] = [5000]
    ensemble_valeurs["primary_reserve_down_oversupplied_cost"] = [5]
    ensemble_valeurs["secondary_reserve_up_not_supplied_cost"] = [5000]
    ensemble_valeurs["secondary_reserve_up_oversupplied_cost"] = [5]
    ensemble_valeurs["secondary_reserve_down_not_supplied_cost"] = [5000]
    ensemble_valeurs["secondary_reserve_down_oversupplied_cost"] = [5]
    ensemble_valeurs["tertiary1_reserve_up_not_supplied_cost"] = [5000]
    ensemble_valeurs["tertiary1_reserve_up_oversupplied_cost"] = [5]
    ensemble_valeurs["tertiary1_reserve_down_not_supplied_cost"] = [5000]
    ensemble_valeurs["tertiary1_reserve_down_oversupplied_cost"] = [5]
    ensemble_valeurs["tertiary2_reserve_up_not_supplied_cost"] = [0]
    ensemble_valeurs["tertiary2_reserve_up_oversupplied_cost"] = [0]
    ensemble_valeurs["tertiary2_reserve_down_not_supplied_cost"] = [0]
    ensemble_valeurs["tertiary2_reserve_down_oversupplied_cost"] = [0]
    ensemble_valeurs["generation_reserve_up_primary_off"] =  [0]
    ensemble_valeurs["generation_reserve_up_secondary_off"] =  [0]
    ensemble_valeurs["generation_reserve_up_tertiary2_off"] =  [0]
    ensemble_valeurs["participation_max_primary_reserve_up_off"] =  [0]
    ensemble_valeurs["participation_max_secondary_reserve_up_off"] =  [0]
    ensemble_valeurs["participation_max_tertiary2_reserve_up_off"] =  [0]
    ensemble_valeurs["cost_participation_primary_reserve_up_off"] =  [0]
    ensemble_valeurs["cost_participation_secondary_reserve_up_off"] =  [0]
    ensemble_valeurs["cost_participation_tertiary2_reserve_up_off"] =  [0]

    ensemble_valeurs["participation_max_primary_reserve_up_on"] =  [14]
    ensemble_valeurs["generation_reserve_up_primary_on"] =  [0]
    ensemble_valeurs["cost_participation_primary_reserve_up_on"] =  [0]
    ensemble_valeurs["participation_max_primary_reserve_down"] =  [14]
    ensemble_valeurs["generation_reserve_down_primary"] =  [0]
    ensemble_valeurs["cost_participation_primary_reserve_down"] =  [0]

    ensemble_valeurs["participation_max_tertiary1_reserve_up_on"] =  [60]
    ensemble_valeurs["generation_reserve_up_tertiary1_on"] =  [96.9540416554936]
    ensemble_valeurs["cost_participation_tertiary1_reserve_up_on"] =  [0]
    ensemble_valeurs["participation_max_tertiary1_reserve_down"] =  [60]
    ensemble_valeurs["generation_reserve_down_tertiary1"] =  [122.060196633772]
    ensemble_valeurs["cost_participation_tertiary1_reserve_down"] =  [0]
    ensemble_valeurs["participation_max_tertiary1_reserve_up_off"] =  [0]
    ensemble_valeurs["generation_reserve_up_tertiary1_off"] =  [0]
    ensemble_valeurs["cost_participation_tertiary1_reserve_up_off"] =  [0]

    ensemble_valeurs["participation_max_secondary_reserve_up_on"] =  [0]
    ensemble_valeurs["generation_reserve_up_secondary_on"] =  [0]
    ensemble_valeurs["cost_participation_secondary_reserve_up_on"] =  [0]
    ensemble_valeurs["participation_max_secondary_reserve_down"] =  [0]
    ensemble_valeurs["generation_reserve_down_secondary"] =  [0]
    ensemble_valeurs["cost_participation_secondary_reserve_down"] =  [0]

    ensemble_valeurs["participation_max_tertiary2_reserve_up_on"] =  [0]
    ensemble_valeurs["generation_reserve_up_tertiary2_on"] =  [0]
    ensemble_valeurs["cost_participation_tertiary2_reserve_up_on"] =  [0]
    ensemble_valeurs["participation_max_tertiary2_reserve_down"] =  [0]
    ensemble_valeurs["generation_reserve_down_tertiary2"] =  [0]
    ensemble_valeurs["cost_participation_tertiary2_reserve_down"] =  [0]

    ensemble_valeurs["spillage_cost"] = [0]
    ensemble_valeurs["min_generating"] = [0]
    ensemble_valeurs["max_generating"] = [410]
    ensemble_valeurs["nb_units_max_invisible"] = [3]
    ensemble_valeurs["nb_units_max"] = [3]



    heuristique_resultat= heuristique_opti_repartition_sans_pmin(
                [0],
                ensemble_valeurs,
                "perte",    # version
                # "choix", # option
                # "réduction", # bonus
                )

    print(heuristique_resultat)