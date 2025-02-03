from tests.generate_mps_files import *
from math import ceil,floor
import numpy as np
from tests.functional.libs.heuristique import *
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    TimeScenarioSeriesData,
)
from tests.functional.libs.lib_thermal_heuristic import (
    THERMAL_CLUSTER_HEURISTIQUE_DMIN,
)
from andromede.thermal_heuristic.problem import (
    BlockScenarioIndex,
    ThermalProblemBuilder,
    TimeScenarioHourParameter,
)
from andromede.thermal_heuristic.time_scenario_parameter import (
    BlockScenarioIndex,
    TimeScenarioHourParameter,
)
from andromede.thermal_heuristic.data import (
    get_max_failures,
    get_max_unit_for_min_down_time,
)
from andromede.simulation import OutputValues


#  446s avec scip
#  483s avec xpress


def test_generation_mps():

    study_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_mfrr_FR_1_week"
    # antares_path = "D:/AppliRTE/bin/antares-solver.exe"
    # output_path = generate_mps_file(study_path,antares_path)
    # output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/Test_simple_noeud_unique/output/20250116-1104exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/Test_simple_noeud_double/output/20250123-1143exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_FR_1week/output/20250124-1152exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_FR_1week_eteint/output/20250127-1411exp-export_mps"
    output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_mfrr_FR_1_week/output/20250130-0937exp-export_mps"

    m = read_mps(output_path,1,0,"XPRESS")
    

    # for nom_cluster in ['FR_CCGT*new','FR_DSR_industrie','FR_Hard*coal*new','FR_Light*oil']:
    #     for t in range(168):
    #         delete_constraint(m, 1, 'POffUnitsLowerBound::area<fr>::ThermalCluster<' + nom_cluster + '>::Reserve<mfrr_up>::hour<'+ str(t) +'>')


    # lp_format = m.ExportModelAsLpFormat(False)
    # with open("model.lp","w") as file:
    #     file.write(lp_format)


    solve_complete_problem(m)
    cost1 = m.Objective().Value()


    thermal_var_production = find_thermal_var(m,"DispatchableProduction")
    thermal_var_nodu = find_thermal_var(m,"NODU")

    thermal_var_reserves_on = find_thermal_var(m,"ParticipationOfRunningUnitsToReserve")
    thermal_var_fcr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_up"]
    thermal_var_fcr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_down"]
    thermal_var_afrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_up"]
    thermal_var_afrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_down"]
    thermal_var_mfrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_up"]
    thermal_var_mfrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_down"]
    thermal_var_reserves_off = find_thermal_var(m,"ParticipationOfOffUnitsToReserve")
    thermal_var_mfrr_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="mfrr_up"]
    thermal_var_tertiary2_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary2_up"]
    thermal_var_tertiary2_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary2_down"]
    
    thermal_areas = get_ini_file(study_path + "/input/thermal/areas.ini")
    
    list_thermal_clusters = thermal_var_production.cluster_name.unique()
    # list_areas_thermique = thermal_var_nodu.name_antares_object.unique()
    # list_thermal_reserve_clusters = thermal_var_reserves_on.cluster_name.unique()
    list_areas_reserve_thermique = ["fr"]
    thermal_list = {}
    reserves_areas_cost = {}

    reserve_cluster = {}
    reserve_cluster["fcr_up"] = {}
    reserve_cluster["fcr_down"] = {}
    reserve_cluster["afrr_up"] = {}
    reserve_cluster["afrr_down"] = {}
    reserve_cluster["mfrr_up"] = {}
    reserve_cluster["mfrr_down"] = {}
    reserve_cluster["tertiary2_up"] = {}
    reserve_cluster["tertiary2_down"] = {}

    for area in list_areas_reserve_thermique:
        thermal_list[area] = get_ini_file(study_path +  "/input/thermal/clusters/" + area + "/list.ini")
        reserves_areas_cost[area] = get_ini_file(study_path + "/input/reserves/" + area + "/reserves.ini")
        with open(study_path +  "/input/thermal/clusters/" + area + "/reserves.ini") as file:
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



    list_cluster_fr = []
    for thermal_cluster in list_thermal_clusters:
        [nom_noeud,nom_cluster] = thermal_cluster.split("_",1)
        if nom_noeud == "fr":
            list_cluster_fr.append(thermal_cluster)





    
    ensemble_valeurs = {}

    for thermal_cluster in list_cluster_fr:
        ensemble_valeurs[thermal_cluster] = {}
        ensemble_valeurs[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["nb_on"] = list(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])
        [nom_noeud,nom_cluster] = thermal_cluster.split("_",1)
        nom_cluster_espace = nom_cluster.replace("*"," ")
        ensemble_valeurs[thermal_cluster]["p_max"] =  [ thermal_list[nom_noeud].getfloat(nom_cluster_espace,"nominalcapacity") for t in range(168)]
        ensemble_valeurs[thermal_cluster]["ens_cost"] =  [ thermal_areas.getfloat('unserverdenergycost',nom_noeud) for t in range(168)]

        if thermal_list[nom_noeud].has_option(nom_cluster_espace,"min-stable-power"):
            ensemble_valeurs[thermal_cluster]["p_min"] =  [ thermal_list[nom_noeud].getfloat(nom_cluster_espace,"min-stable-power") for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["p_min"] = [ 0 for t in range(168)]
        if thermal_list[nom_noeud].has_option(nom_cluster_espace,"min-up-time"):
            ensemble_valeurs[thermal_cluster]["dmin_up"] = thermal_list[nom_noeud].getint(nom_cluster_espace,"min-up-time")
        else:
            ensemble_valeurs[thermal_cluster]["dmin_up"] = 1
        if thermal_list[nom_noeud].has_option(nom_cluster_espace,"min-down-time"):
            ensemble_valeurs[thermal_cluster]["dmin_down"] = thermal_list[nom_noeud].getint(nom_cluster_espace,"min-down-time")
        else:
            ensemble_valeurs[thermal_cluster]["dmin_down"] = 1
        if thermal_list[nom_noeud].has_option(nom_cluster_espace,"market-bid-cost"):
            ensemble_valeurs[thermal_cluster]["cost"] =  [ thermal_list[nom_noeud].getfloat(nom_cluster_espace,"market-bid-cost") for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["cost"] = [ 0 for t in range(168)]
        if thermal_list[nom_noeud].has_option(nom_cluster_espace,"startup-cost"):
            ensemble_valeurs[thermal_cluster]["startup_cost"] =  [ thermal_list[nom_noeud].getfloat(nom_cluster_espace,"startup-cost") for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["startup_cost"] = [ 0 for t in range(168)]
        if thermal_list[nom_noeud].has_option(nom_cluster_espace,"fixed-cost"):
            ensemble_valeurs[thermal_cluster]["fixed_cost"] =  [ thermal_list[nom_noeud].getfloat(nom_cluster_espace,"fixed-cost") for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["fixed_cost"] =  [ 0 for t in range(168)]
        

        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('fcr_up','failure-cost'):
            ensemble_valeurs[thermal_cluster]["primary_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('fcr_up','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["primary_reserve_up_not_supplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('fcr_up','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["primary_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('fcr_up','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["primary_reserve_up_oversupplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('fcr_down','failure-cost'):
            ensemble_valeurs[thermal_cluster]["primary_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('fcr_down','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["primary_reserve_down_not_supplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('fcr_down','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["primary_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('fcr_down','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["primary_reserve_down_oversupplied_cost"] = [ 0 for t in range(168)]


        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('afrr_up','failure-cost'):
            ensemble_valeurs[thermal_cluster]["secondary_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('afrr_up','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["secondary_reserve_up_not_supplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('afrr_up','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["secondary_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('afrr_up','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["secondary_reserve_up_oversupplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('afrr_down','failure-cost'):
            ensemble_valeurs[thermal_cluster]["secondary_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('afrr_down','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["secondary_reserve_down_not_supplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('afrr_down','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["secondary_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('afrr_down','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["secondary_reserve_down_oversupplied_cost"] = [ 0 for t in range(168)]

        
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('mfrr_up','failure-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('mfrr_up','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_not_supplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('mfrr_up','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('mfrr_up','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_oversupplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('mfrr_down','failure-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('mfrr_down','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_not_supplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('mfrr_down','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('mfrr_down','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_oversupplied_cost"] = [ 0 for t in range(168)]



        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('tertiary2_up','failure-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary2_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('tertiary2_up','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary2_reserve_up_not_supplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('tertiary2_up','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary2_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('tertiary2_up','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary2_reserve_up_oversupplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('tertiary2_down','failure-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary2_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('tertiary2_down','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary2_reserve_down_not_supplied_cost"] = [ 0 for t in range(168)]
        if (nom_noeud in reserves_areas_cost) and reserves_areas_cost[nom_noeud].has_option('tertiary2_down','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary2_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('tertiary2_down','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary2_reserve_down_oversupplied_cost"] = [ 0 for t in range(168)]


        ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_up_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_up_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_up_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_off"] =  [ 0 for t in range(168)]


        if (nom_cluster_espace in reserve_cluster["fcr_up"]) and ('max-power' in reserve_cluster["fcr_up"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_on"] = [ reserve_cluster["fcr_up"][nom_cluster_espace]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_fcr_up_on.loc[thermal_var_fcr_up_on["cluster_name"]==thermal_cluster]["sol"])
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_up_on"] =  [ reserve_cluster["fcr_up"][nom_cluster_espace]['participation-cost'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_on"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_up_on"] =  [ 0 for t in range(168)]
        if (nom_cluster_espace in reserve_cluster["fcr_down"]) and ('max-power' in reserve_cluster["fcr_down"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_down"] = [ reserve_cluster["fcr_down"][nom_cluster_espace]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_fcr_down_on.loc[thermal_var_fcr_down_on["cluster_name"]==thermal_cluster]["sol"])
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_down"] =  [ reserve_cluster["fcr_down"][nom_cluster_espace]['participation-cost'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_down"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_down"] =  [ 0 for t in range(168)]


        if (nom_cluster_espace in reserve_cluster["mfrr_up"]) and ('max-power' in reserve_cluster["mfrr_up"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_on"] = [ reserve_cluster["mfrr_up"][nom_cluster_espace]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_mfrr_up_on.loc[thermal_var_mfrr_up_on["cluster_name"]==thermal_cluster]["sol"])
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_on"] =  [ reserve_cluster["mfrr_up"][nom_cluster_espace]['participation-cost'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_on"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_on"] =  [ 0 for t in range(168)]
        if (nom_cluster_espace in reserve_cluster["mfrr_down"]) and ('max-power' in reserve_cluster["mfrr_down"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_down"] = [ reserve_cluster["mfrr_down"][nom_cluster_espace]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"] = list(thermal_var_mfrr_down_on.loc[thermal_var_mfrr_down_on["cluster_name"]==thermal_cluster]["sol"])
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_down"] =  [ reserve_cluster["mfrr_down"][nom_cluster_espace]['participation-cost'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_down"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_down"] =  [ 0 for t in range(168)]        
        if (nom_cluster_espace in reserve_cluster["mfrr_up"]) and ('max-power-off' in reserve_cluster["mfrr_up"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_off"] =  [ reserve_cluster["mfrr_up"][nom_cluster_espace]['max-power-off'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_mfrr_up_off.loc[thermal_var_mfrr_up_off["cluster_name"]==thermal_cluster]["sol"])
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_off"] =  [ reserve_cluster["mfrr_up"][nom_cluster_espace]['participation-cost-off'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_off"] =  [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_off"] =  [ 0 for t in range(168)]


        if (nom_cluster_espace in reserve_cluster["afrr_up"]) and ('max-power' in reserve_cluster["afrr_up"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_up_on"] = [ reserve_cluster["afrr_up"][nom_cluster_espace]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"] = list(thermal_var_afrr_up_on.loc[thermal_var_afrr_up_on["cluster_name"]==thermal_cluster]["sol"])
            ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_up_on"] =  [ reserve_cluster["afrr_up"][nom_cluster_espace]['participation-cost'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_up_on"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_up_on"] =  [ 0 for t in range(168)]
        if (nom_cluster_espace in reserve_cluster["afrr_down"]) and ('max-power' in reserve_cluster["afrr_down"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_down"] = [ reserve_cluster["afrr_down"][nom_cluster_espace]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"] = list(thermal_var_afrr_down_on.loc[thermal_var_afrr_down_on["cluster_name"]==thermal_cluster]["sol"])
            ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_down"] =  [ reserve_cluster["afrr_down"][nom_cluster_espace]['participation-cost'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_down"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_down"] =  [ 0 for t in range(168)]


        if (nom_cluster_espace in reserve_cluster["tertiary2_up"]) and ('max-power' in reserve_cluster["tertiary2_up"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_on"] = [ reserve_cluster["tertiary2_up"][nom_cluster_espace]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_on"] = list(thermal_var_tertiary2_up_on.loc[thermal_var_tertiary2_up_on["cluster_name"]==thermal_cluster]["sol"])
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_on"] =  [ reserve_cluster["tertiary2_up"][nom_cluster_espace]['participation-cost'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_on"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_on"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_on"] =  [ 0 for t in range(168)]
        if (nom_cluster_espace in reserve_cluster["tertiary2_down"]) and ('max-power' in reserve_cluster["tertiary2_down"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_down"] = [ reserve_cluster["tertiary2_down"][nom_cluster_espace]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary2"] = list(thermal_var_tertiary2_down_on.loc[thermal_var_tertiary2_down_on["cluster_name"]==thermal_cluster]["sol"])
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_down"] =  [ reserve_cluster["tertiary2_down"][nom_cluster_espace]['participation-cost'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_down"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary2"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_down"] =  [ 0 for t in range(168)]
      
         
        ensemble_valeurs[thermal_cluster]["spillage_cost"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["min_generating"] =  [ 0 for t in range(168)]
        
        if nom_cluster == "FR_VE_inj":
            disponibilite_puissance = np.array([1 for t in range (168)])
        else:
            disponibilite_puissance = np.loadtxt(study_path +  "/input/thermal/series/"+ nom_noeud +"/" + nom_cluster_espace + "/series.txt")[0:168,0]
        ensemble_valeurs[thermal_cluster]["max_generating"] = disponibilite_puissance
        ensemble_valeurs[thermal_cluster]["nb_units_max_invisible"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["ub"])
        ensemble_valeurs[thermal_cluster]["nb_units_max"] = ensemble_valeurs[thermal_cluster]["nb_units_max_invisible"]




    for thermal_cluster in list_cluster_fr: 
        de_accurate_base = pd.DataFrame(data = {"energy_generation":ensemble_valeurs[thermal_cluster]["energy_generation"],
                                                "nodu":ensemble_valeurs[thermal_cluster]["nb_on"],
                                                "generation_reserve_up_primary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"],
                                                "generation_reserve_down_primary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"],
                                                "generation_reserve_up_secondary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"],
                                                "generation_reserve_down_secondary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"],
                                                "generation_reserve_up_tertiary1_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"],
                                                "generation_reserve_down_tertiary1":ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"],
                                                "generation_reserve_up_tertiary1_off":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"]})
        de_accurate_base.to_csv("result_step1" + thermal_cluster.replace("*","_") + ".csv",index=False)





    heuristique_resultat = {}
    nbr_heuristique = {}
    nbr_on_final = {}

    for thermal_cluster in list_thermal_clusters:
        if not(thermal_cluster in list_cluster_fr):
            nbr_on_final[thermal_cluster] = list(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])

            id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
            for hour, id in enumerate(id_var):
                # variable = all_vars[thermal_var_nodu["id_var"]==id_var]
                change_lower_bound(m,id,nbr_on_final[thermal_cluster][hour])
                change_upper_bound(m,id,nbr_on_final[thermal_cluster][hour])


    for thermal_cluster in list_cluster_fr: #list_cluster_enabled
        heuristique_resultat[thermal_cluster] = old_heuristique(
            [t for t in range(168)],
            ensemble_valeurs[thermal_cluster],
            # "perte",    # version
            # "choix", # option
            # "réduction", # bonus
            )
        
        nbr_heuristique[thermal_cluster] = []
        for t in range(168):
            nbr_heuristique[thermal_cluster].append(heuristique_resultat[thermal_cluster][t][0])


        p_max = pd.DataFrame(
            np.transpose(ensemble_valeurs[thermal_cluster]["p_max"]),
            index=[i for i in range(168)],
        )
        nb_units_min = pd.DataFrame(
            np.transpose([heuristique_resultat[thermal_cluster][t][0] for t in range(168)]),
            index=[i for i in range(168)],
        )
        nb_units_max = pd.DataFrame(
            np.transpose(ensemble_valeurs[thermal_cluster]["nb_units_max"]),
            index=[i for i in range(168)],
        )

        database = DataBase()
        p_min = ensemble_valeurs[thermal_cluster]["p_min"][0]
        database.add_data(thermal_cluster, "p_min", ConstantData(p_min))
        database.add_data(thermal_cluster, "d_min_up", ConstantData(ensemble_valeurs[thermal_cluster]["dmin_up"]))
        database.add_data(thermal_cluster, "d_min_down", ConstantData(ensemble_valeurs[thermal_cluster]["dmin_down"]))
        database.add_data(thermal_cluster, "nb_units_max", TimeScenarioSeriesData(nb_units_max))
        database.add_data(thermal_cluster, "p_max", TimeScenarioSeriesData(p_max))
        database.add_data(thermal_cluster, "nb_units_min", TimeScenarioSeriesData(nb_units_min))



        nb_units_max_min_down_time = get_max_unit_for_min_down_time(ensemble_valeurs[thermal_cluster]["dmin_down"],nb_units_max,168)
        database.add_data(thermal_cluster, "nb_units_max_min_down_time", TimeScenarioSeriesData(nb_units_max_min_down_time))

        max_failure = get_max_failures(nb_units_max,168)
        database.add_data(thermal_cluster, "max_failure", TimeScenarioSeriesData(max_failure))


        thermal_problem_builder = ThermalProblemBuilder(
            network=Network("test"),
            database=database,
            time_scenario_hour_parameter=TimeScenarioHourParameter(0, 0, 168),
        )


        # Solve heuristic problem
        resolution_step_accurate_heuristic = (
            thermal_problem_builder.heuristic_resolution_step(
                BlockScenarioIndex(0, 0),
                id_component=thermal_cluster,
                model=THERMAL_CLUSTER_HEURISTIQUE_DMIN,
            )
        )
        status = resolution_step_accurate_heuristic.solver.Solve()
        assert status == pywraplp.Solver.OPTIMAL



        nbr_on_final[thermal_cluster] = OutputValues(resolution_step_accurate_heuristic)._components[thermal_cluster]._variables['nb_on'].value[0]

        id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
        for hour, id in enumerate(id_var):
            # variable = all_vars[thermal_var_nodu["id_var"]==id_var]
            change_lower_bound(m,id,ceil(nbr_on_final[thermal_cluster][hour]))
            change_upper_bound(m,id,ceil(nbr_on_final[thermal_cluster][hour]))
    

    de_accurate_heuristique = pd.DataFrame(data = nbr_heuristique)
    de_accurate_heuristique.to_csv("result_mps_heuristique.csv",index=False)

    lp_format = m.ExportModelAsLpFormat(False)
    with open("model_2.lp","w") as file:
        file.write(lp_format)


    solve_complete_problem(m)
    cost2 = m.Objective().Value()


    cost = [cost1,cost2]


    de_accurate_base = pd.DataFrame(data = {"Fonction_objectif":cost})
    de_accurate_base.to_csv("result_mps_base.csv",index=False)


    thermal_var_production = find_thermal_var(m,"DispatchableProduction")
    thermal_var_nodu = find_thermal_var(m,"NODU")

    thermal_var_reserves_on = find_thermal_var(m,"ParticipationOfRunningUnitsToReserve")
    thermal_var_fcr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_up"]
    thermal_var_fcr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_down"]
    thermal_var_afrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_up"]
    thermal_var_afrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_down"]
    thermal_var_mfrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_up"]
    thermal_var_mfrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_down"]
    thermal_var_reserves_off = find_thermal_var(m,"ParticipationOfOffUnitsToReserve")
    thermal_var_mfrr_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="mfrr_up"]
    thermal_var_tertiary2_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary2_up"]
    thermal_var_tertiary2_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary2_down"]
    
    thermal_areas = get_ini_file(study_path + "/input/thermal/areas.ini")
    


    for thermal_cluster in list_cluster_fr:
        ensemble_valeurs[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["nb_on"] = list(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])
        [nom_noeud,nom_cluster] = thermal_cluster.split("_",1)
        nom_cluster_espace = nom_cluster.replace("*"," ")
        if (nom_cluster_espace in reserve_cluster["fcr_up"]) and ('max-power' in reserve_cluster["fcr_up"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_fcr_up_on.loc[thermal_var_fcr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if (nom_cluster_espace in reserve_cluster["fcr_down"]) and ('max-power' in reserve_cluster["fcr_down"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_fcr_down_on.loc[thermal_var_fcr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if (nom_cluster_espace in reserve_cluster["mfrr_up"]) and ('max-power' in reserve_cluster["mfrr_up"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_mfrr_up_on.loc[thermal_var_mfrr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if (nom_cluster_espace in reserve_cluster["mfrr_down"]) and ('max-power' in reserve_cluster["mfrr_down"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"] = list(thermal_var_mfrr_down_on.loc[thermal_var_mfrr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if (nom_cluster_espace in reserve_cluster["mfrr_up"]) and ('max-power-off' in reserve_cluster["mfrr_up"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_mfrr_up_off.loc[thermal_var_mfrr_up_off["cluster_name"]==thermal_cluster]["sol"])
        if (nom_cluster_espace in reserve_cluster["afrr_up"]) and ('max-power' in reserve_cluster["afrr_up"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"] = list(thermal_var_afrr_up_on.loc[thermal_var_afrr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if (nom_cluster_espace in reserve_cluster["afrr_down"]) and ('max-power' in reserve_cluster["afrr_down"][nom_cluster_espace]):
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"] = list(thermal_var_afrr_down_on.loc[thermal_var_afrr_down_on["cluster_name"]==thermal_cluster]["sol"])
 
        de_accurate_peak = pd.DataFrame(data = {"energy_generation":ensemble_valeurs[thermal_cluster]["energy_generation"],
                                                "nodu":ensemble_valeurs[thermal_cluster]["nb_on"],
                                                "generation_reserve_up_primary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"],
                                                "generation_reserve_down_primary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"],
                                                "generation_reserve_up_secondary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"],
                                                "generation_reserve_down_secondary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"],
                                                "generation_reserve_up_tertiary1_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"],
                                                "generation_reserve_down_tertiary1":ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"],
                                                "generation_reserve_up_tertiary1_off":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"]})
        de_accurate_peak.to_csv("result_step2" + thermal_cluster.replace("*","_") + ".csv",index=False)

    somme = {}
    somme["energy_generation"] = [ 0 for t in range(168)]
    somme["generation_reserve_up_primary_on"] = [ 0 for t in range(168)]
    somme["generation_reserve_down_primary"] = [ 0 for t in range(168)]
    somme["generation_reserve_up_secondary_on"] = [ 0 for t in range(168)]
    somme["generation_reserve_down_secondary"] = [ 0 for t in range(168)]
    somme["generation_reserve_up_tertiary1_on"] = [ 0 for t in range(168)]
    somme["generation_reserve_down_tertiary1"] = [ 0 for t in range(168)]
    for thermal_cluster in list_cluster_fr:
        for t in range(168):
            somme["energy_generation"][t] += ensemble_valeurs[thermal_cluster]["energy_generation"][t]
            somme["generation_reserve_up_primary_on"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"][t]
            somme["generation_reserve_down_primary"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"][t]
            somme["generation_reserve_up_secondary_on"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"][t]
            somme["generation_reserve_down_secondary"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"][t]
            somme["generation_reserve_up_tertiary1_on"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"][t]
            somme["generation_reserve_down_tertiary1"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"][t]
            somme["generation_reserve_up_tertiary1_on"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"][t]

    de_accurate_somme = pd.DataFrame(data = somme)
    de_accurate_somme.to_csv("result_step2_somme" + ".csv",index=False)