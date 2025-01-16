from tests.generate_mps_files import *
from math import ceil,floor
from pathlib import Path
from typing import List
import numpy as np
from tests.functional.libs.heuristique import *


def test_generation_mps():

    study_path = "C:/Users/sonvicoleo/Documents/Test_finaux/Test_simple_noeud_unique"
    antares_path = "D:/AppliRTE/bin/antares-solver.exe"
    # output_path = generate_mps_file(study_path,antares_path)
    output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/Test_simple_noeud_unique/output/20250116-1104exp-export_mps"

    m = read_mps(output_path,1,0,"SCIP")
    
    thermal_var_production = find_thermal_var(m,"DispatchableProduction")

    list_thermal_clusters = thermal_var_production.cluster_name.unique()

    for thermal_cluster in list_thermal_clusters:
        for t in range(168):
            [nom_noeud,nom_cluster] = thermal_cluster.split("_")
            delete_constraint(m, 1, 'POffUnitsLowerBound::area<' + nom_noeud + '>::ThermalCluster<' + nom_cluster + '>::Reserve<tertiary_up>::hour<'+ str(t) +'>')


    lp_format = m.ExportModelAsLpFormat(False)
    with open("model.lp","w") as file:
        file.write(lp_format)


    solve_complete_problem(m)
    cost = m.Objective().Value()

    # all_vars = inspect_variables(m)
    # nom_variables = all_vars.name_var.unique()

    thermal_var_production = find_thermal_var(m,"DispatchableProduction")
    thermal_var_nodu = find_thermal_var(m,"NODU")
    thermal_var_reserves_on = find_thermal_var(m,"ParticipationOfRunningUnitsToReserve")
    thermal_var_primary_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="primary_up"]
    thermal_var_primary_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="primary_down"]
    thermal_var_tertiary_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary_up"]
    thermal_var_tertiary_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary_down"]
    thermal_var_reserves_off = find_thermal_var(m,"ParticipationOfOffUnitsToReserve")
    thermal_var_tertiary_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="tertiary_up"]
    

    
    thermal_list = get_ini_file(study_path +  "/input/thermal/clusters/area/list.ini")
    # thermal_reserve = get_ini_file(study_path +  "/input/thermal/clusters/area/reserves.ini")
    thermal_areas = get_ini_file(study_path + "/input/thermal/areas.ini")
    reserves_areas_cost = get_ini_file(study_path + "/input/reserves/area/reserves.ini")
    # thermal_reserve = np.loadtxt(study_path +  "/input/thermal/clusters/area/reserves.ini")



    reserve_cluster = {}
    reserve_cluster["primary_up"] = {}
    reserve_cluster["primary_down"] = {}
    reserve_cluster["tertiary_up"] = {}
    reserve_cluster["tertiary_down"] = {}

    with open(study_path +  "/input/thermal/clusters/area/reserves.ini") as file:
        # reserve = file.readline().split("[")[1].split("]")[0]
        # cluster = file.readline().split("= ")[1].strip()
        # reserve_cluster[reserve][cluster] = {}
        # ligne = file.readline()
        # nbr_ligne = 2
        liste_reserves_cluster = file.read().split("[")
        for bloc_reserve in range(1,len(liste_reserves_cluster)):
            lignes = liste_reserves_cluster[bloc_reserve].split("\n")
            reserve = lignes[0].split("]")[0]
            cluster = lignes[1].split(" = ")[1]
            reserve_cluster[reserve][cluster] = {}
            for numero_ligne in range(2,len(lignes)):
                ligne = lignes[numero_ligne]
                if ligne != '':
                    [parametre,valeur] = ligne.split(" = ")
                    reserve_cluster[reserve][cluster][parametre] = float(valeur)


    sections = thermal_list.sections()
    

    ensemble_valeurs = {}

    for thermal_cluster in list_thermal_clusters:
        ensemble_valeurs[thermal_cluster] = {}
        ensemble_valeurs[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["nb_on"] = list(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_primary_up_on.loc[thermal_var_primary_up_on["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_primary_down_on.loc[thermal_var_primary_down_on["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_tertiary_up_on.loc[thermal_var_tertiary_up_on["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"] =list(thermal_var_tertiary_down_on.loc[thermal_var_tertiary_down_on["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_on"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary2"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_tertiary_up_off.loc[thermal_var_tertiary_up_off["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_off"] =  [ 0 for t in range(168)]
        [nom_noeud,nom_cluster] = thermal_cluster.split("_")
        ensemble_valeurs[thermal_cluster]["p_max"] =  [ thermal_list.getfloat(nom_cluster,"nominalcapacity") for t in range(168)]
        ensemble_valeurs[thermal_cluster]["p_min"] =  [ thermal_list.getfloat(nom_cluster,"min-stable-power") for t in range(168)]
        if thermal_list.has_option(nom_cluster,"min-up-time"):
            ensemble_valeurs[thermal_cluster]["dmin_up"] = thermal_list.getfloat(nom_cluster,"min-up-time")
        else:
            ensemble_valeurs[thermal_cluster]["dmin_up"] = 1
        if thermal_list.has_option(nom_cluster,"min-down-time"):
            ensemble_valeurs[thermal_cluster]["dmin_down"] = thermal_list.getfloat(nom_cluster,"min-down-time")
        else:
            ensemble_valeurs[thermal_cluster]["dmin_down"] = 1
        ensemble_valeurs[thermal_cluster]["cost"] =  [ thermal_list.getfloat(nom_cluster,"marginal-cost") for t in range(168)]
        ensemble_valeurs[thermal_cluster]["startup_cost"] =  [ thermal_list.getfloat(nom_cluster,"startup-cost") for t in range(168)]
        if thermal_list.has_option(nom_cluster,"fixed-cost"):
            ensemble_valeurs[thermal_cluster]["fixed_cost"] =  [ thermal_list.getfloat(nom_cluster,"fixed-cost") for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["fixed_cost"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["ens_cost"] =  [ thermal_areas.getfloat('unserverdenergycost',nom_noeud) for t in range(168)]
        ensemble_valeurs[thermal_cluster]["primary_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost.getfloat('primary_up','failure-cost') for t in range(168)]
        ensemble_valeurs[thermal_cluster]["primary_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost.getfloat('primary_up','spillage-cost') for t in range(168)]
        ensemble_valeurs[thermal_cluster]["primary_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost.getfloat('primary_down','failure-cost') for t in range(168)]
        ensemble_valeurs[thermal_cluster]["primary_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost.getfloat('primary_down','spillage-cost') for t in range(168)]
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost.getfloat('tertiary_up','failure-cost') for t in range(168)]
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost.getfloat('tertiary_up','spillage-cost') for t in range(168)]
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost.getfloat('tertiary_down','failure-cost') for t in range(168)]
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost.getfloat('tertiary_down','spillage-cost') for t in range(168)]
        ensemble_valeurs[thermal_cluster]["secondary_reserve_up_not_supplied_cost"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["secondary_reserve_up_oversupplied_cost"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["secondary_reserve_down_not_supplied_cost"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["secondary_reserve_down_oversupplied_cost"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_up_not_supplied_cost"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_up_oversupplied_cost"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_down_not_supplied_cost"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_down_oversupplied_cost"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_on"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary2"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_on"] =  [ reserve_cluster["primary_up"][nom_cluster]['max-power'] for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_down"] =  [ reserve_cluster["primary_down"][nom_cluster]['max-power'] for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_on"] =  [ reserve_cluster["tertiary_up"][nom_cluster]['max-power'] for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_down"] =  [ reserve_cluster["tertiary_down"][nom_cluster]['max-power'] for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_off"] =  [ reserve_cluster["tertiary_up"][nom_cluster]['max-power-off'] for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_up_on"] =  [ reserve_cluster["primary_up"][nom_cluster]['participation-cost'] for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_down"] =  [ reserve_cluster["primary_down"][nom_cluster]['participation-cost'] for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_on"] =  [ reserve_cluster["tertiary_up"][nom_cluster]['participation-cost'] for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_down"] =  [ reserve_cluster["tertiary_down"][nom_cluster]['participation-cost'] for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_off"] =  [ reserve_cluster["tertiary_up"][nom_cluster]['participation-cost-off'] for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_up_on"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_down"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_on"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_down"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_up_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_up_on"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_down"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_on"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_down"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_up_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_up_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["spillage_cost"] =  [ 0 for t in range(168)]

        disponibilite_puissance = np.loadtxt(study_path +  "/input/thermal/series/area/" + nom_cluster + "/series.txt")[0:168]
        disponibilite = np.ceil(disponibilite_puissance / ensemble_valeurs[thermal_cluster]["p_max"])
        ensemble_valeurs[thermal_cluster]["nbr_max"] = disponibilite





    heuristique_resultat = {}

    for thermal_cluster in list_thermal_clusters:
        heuristique_resultat[thermal_cluster] = nouvel_appel_heuristique(old_heuristique,ensemble_valeurs[thermal_cluster])





    # voir test_resolution_with_different_scenarios la fonction generate_database





    for thermal_cluster in list_thermal_clusters:
        id_var = thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster,"id_var"]
        p_min = thermal_list.getfloat("peak","min-stable-power")
        for hour, id in enumerate(id_var):
            change_lower_bound(m,id,heuristique_resultat[thermal_cluster][hour] * p_min)
    


    solve_complete_problem(m)
    thermal_var = find_thermal_var(m,"DispatchableProduction")
    for thermal_cluster in list_thermal_clusters:
        sol_itr_1 = thermal_var.loc[thermal_var["cluster_name"]==thermal_cluster,"sol"]/97

    print(sol_itr_1)