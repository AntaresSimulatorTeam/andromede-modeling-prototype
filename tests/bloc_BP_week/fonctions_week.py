from tests.generate_mps_files import *


def lecture_resultat_semaine(var,list_cluster,ensemble_valeur_annuel):

    (thermal_var_production,thermal_var_nodu,thermal_var_reserves_on,thermal_var_reserves_off) = find_var(var,["DispatchableProduction","NODU","ParticipationOfRunningUnitsToReserve","ParticipationOfOffUnitsToReserve"])
    thermal_var_fcr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_up"]
    thermal_var_fcr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_down"]
    thermal_var_afrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_up"]
    thermal_var_afrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_down"]
    thermal_var_mfrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_up"]
    thermal_var_mfrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_down"]
    thermal_var_mfrr_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="mfrr_up"]
    thermal_var_new_rr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="new_rr_up"]
    thermal_var_new_rr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="new_rr_down"]
    thermal_var_new_rr_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="new_rr_up"]

    ensemble_valeur_semaine = {}

    for thermal_cluster in list_cluster:
        ensemble_valeur_semaine[thermal_cluster] = {}
        ensemble_valeur_semaine[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeur_semaine[thermal_cluster]["nb_on"] = list(round(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"],6))
        ensemble_valeur_semaine[thermal_cluster]["min_generating"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["lb"])
        ensemble_valeur_semaine[thermal_cluster]["max_generating"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["ub"])
        ensemble_valeur_semaine[thermal_cluster]["nb_units_max_invisible"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["ub"])
        ensemble_valeur_semaine[thermal_cluster]["nb_units_max"] = ensemble_valeur_semaine[thermal_cluster]["nb_units_max_invisible"]

        if ensemble_valeur_annuel[thermal_cluster]["participation_max_primary_reserve_up_on"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_fcr_up_on.loc[thermal_var_fcr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_primary_reserve_down"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_fcr_down_on.loc[thermal_var_fcr_down_on["cluster_name"]==thermal_cluster]["sol"])

        if ensemble_valeur_annuel[thermal_cluster]["participation_max_secondary_reserve_up_on"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] = list(thermal_var_afrr_up_on.loc[thermal_var_afrr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_secondary_reserve_down"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] = list(thermal_var_afrr_down_on.loc[thermal_var_afrr_down_on["cluster_name"]==thermal_cluster]["sol"])

        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_up_on"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_mfrr_up_on.loc[thermal_var_mfrr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_down"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] = list(thermal_var_mfrr_down_on.loc[thermal_var_mfrr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_up_off"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_mfrr_up_off.loc[thermal_var_mfrr_up_off["cluster_name"]==thermal_cluster]["sol"])

        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_up_on"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] = list(thermal_var_new_rr_up_on.loc[thermal_var_new_rr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_down"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] = list(thermal_var_new_rr_down_on.loc[thermal_var_new_rr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_up_off"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"] = list(thermal_var_new_rr_up_off.loc[thermal_var_new_rr_up_off["cluster_name"]==thermal_cluster]["sol"])

    return ensemble_valeur_semaine

def lecture_resultat_defaillance(var):
    heure_defaillance = [0] * 9
    quantite_defaillance = [0] * 9
    for i in range(len(var)):
        var_name = var[i].name()
        quantite = var[i].solution_value()
        if "PositiveUnsuppliedEnergy::area<fr>:" in var_name:
            defaillance_prod = quantite
            if defaillance_prod > 0:
                heure_defaillance[0] += 1
                quantite_defaillance[0] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<fcr_up>:" in var_name:
            defaillance_fcr_up = quantite
            if defaillance_fcr_up > 0:
                heure_defaillance[1] += 1
                quantite_defaillance[1] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<fcr_down>:" in var_name:
            defaillance_fcr_down = quantite
            if defaillance_fcr_down > 0:
                heure_defaillance[2] += 1
                quantite_defaillance[2] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<afrr_up>:" in var_name:
            defaillance_afrr_up = quantite
            if defaillance_afrr_up > 0:
                heure_defaillance[3] += 1
                quantite_defaillance[3] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<afrr_down>:" in var_name:
            defaillance_afrr_down = quantite
            if defaillance_afrr_down > 0:
                heure_defaillance[4] += 1
                quantite_defaillance[4] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<mfrr_up>:" in var_name:
            defaillance_mfrr_up = quantite
            if defaillance_mfrr_up > 0:
                heure_defaillance[5] += 1
                quantite_defaillance[5] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<mfrr_down>:" in var_name:
            defaillance_mfrr_down = quantite
            if defaillance_mfrr_down > 0:
                heure_defaillance[6] += 1
                quantite_defaillance[6] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<new_rr_up>:" in var_name:
            defaillance_rr_up = quantite
            if defaillance_rr_up > 0:
                heure_defaillance[7] += 1
                quantite_defaillance[7] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<new_rr_down>:" in var_name:
            defaillance_rr_down = quantite
            if defaillance_rr_down > 0:
                heure_defaillance[8] += 1
                quantite_defaillance[8] += quantite
    return(heure_defaillance,quantite_defaillance)

def affichage_valeur_hebdomadaire(ensemble_valeur_annuel,ensemble_valeur_semaine,list_cluster,nom_debut_csv):
    for thermal_cluster in list_cluster: 
        ensemble_valeur = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]
        de_accurate_base = pd.DataFrame(data = {
                                                "energy_generation":ensemble_valeur["energy_generation"],
                                                "nodu":ensemble_valeur["nb_on"],
                                                "generation_reserve_up_primary_on":ensemble_valeur["generation_reserve_up_primary_on"],
                                                "generation_reserve_down_primary":ensemble_valeur["generation_reserve_down_primary"],
                                                "generation_reserve_up_secondary_on":ensemble_valeur["generation_reserve_up_secondary_on"],
                                                "generation_reserve_down_secondary":ensemble_valeur["generation_reserve_down_secondary"],
                                                "generation_reserve_up_tertiary1_on":ensemble_valeur["generation_reserve_up_tertiary1_on"],
                                                "generation_reserve_down_tertiary1":ensemble_valeur["generation_reserve_down_tertiary1"],
                                                "generation_reserve_up_tertiary1_off":ensemble_valeur["generation_reserve_up_tertiary1_off"],
                                                "generation_reserve_up_tertiary2_on":ensemble_valeur["generation_reserve_up_tertiary2_on"],
                                                "generation_reserve_down_tertiary2":ensemble_valeur["generation_reserve_down_tertiary2"],
                                                "generation_reserve_up_tertiary2_off":ensemble_valeur["generation_reserve_up_tertiary2_off"]
                                                })
        de_accurate_base.to_csv(nom_debut_csv + thermal_cluster.replace("*","_") + ".csv",index=False)


# def heuristiques(heuristique,list_cluster,ensemble_valeur_annuel,ensemble_valeur_semaine):
    # for thermal_cluster in list_cluster:
    #     ensemble_valeurs = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]

    #     heuristique_resultat = heuristique
        
    #     nbr_heuristique[thermal_cluster] = []
    #     for t in range(168):
    #         nbr_heuristique[thermal_cluster].append(heuristique_resultat[t][0])
    
    # temps_heuristique_arrondi_fr_new = time.perf_counter()

    # for thermal_cluster in list_cluster:
    #     ensemble_valeurs = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]
    #     if ((ensemble_valeurs["dmin_up"] == 1) and (ensemble_valeurs["dmin_down"] == 1)) or (nbr_heuristique[thermal_cluster] == list([nbr_heuristique[thermal_cluster][0]] * 168)):
    #         nbr_on_final[thermal_cluster] = nbr_heuristique[thermal_cluster]
    #     else:
    #         nbr_on_final[thermal_cluster] = heuristique_dmin_accurate(ensemble_valeurs,nbr_heuristique[thermal_cluster])

    # temps_heuristique_dmin_fr_new = time.perf_counter()


    # for thermal_cluster in list_cluster:
    #     id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
    #     for hour, id in enumerate(id_var):
    #         change_lower_bound(var,id,ceil(nbr_on_final[thermal_cluster][hour]))
    #         change_upper_bound(var,id,ceil(nbr_on_final[thermal_cluster][hour]))
    
    # temps_changement_borne_fr_new = time.perf_counter()