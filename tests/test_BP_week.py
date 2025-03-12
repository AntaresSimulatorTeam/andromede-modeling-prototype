from tests.generate_mps_files import *
from math import ceil
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
    timesteps,
)
from andromede.thermal_heuristic.data import (
    get_max_failures,
    get_max_unit_for_min_down_time,
)

from andromede.study import (
    ConstantData,
    DataBase,
    TimeScenarioSeriesData,
)
import time

from andromede.simulation.optimization import (
    OptimizationContext,
)
from andromede.simulation import (
    BlockBorderManagement,
    OptimizationProblem,
    OutputValues,
    TimeBlock,
    build_problem,
)
from andromede.study import ConstantData, DataBase, Network, create_component

def lecture_donnees_accurate(study_path):

    

    thermal_areas = get_ini_file(study_path + "/input/thermal/areas.ini")
    list_area = thermal_areas.options('unserverdenergycost')
    list_area.append('ve_vhr_storage')
    list_area.append('y_nuc_modulation')
    list_area.append('z_batteries_pcomp')
    list_area.append('z_effacement')
    list_area.append('z_report')

    ensemble_dmins_etranger = {}
    for area in list_area:
        if area != 'fr':
            thermal_list_area = get_ini_file(study_path +  "/input/thermal/clusters/" + area + "/list.ini")
            list_nom_cluster = thermal_list_area.sections()
            for nom_cluster in list_nom_cluster:
                if thermal_list_area.has_option(nom_cluster,"min-up-time"):
                    dmin_up = thermal_list_area.getint(nom_cluster,"min-up-time")
                else:
                    dmin_up = 1
                if thermal_list_area.has_option(nom_cluster,"min-down-time"):
                    dmin_down = thermal_list_area.getint(nom_cluster,"min-down-time")
                else:
                    dmin_down = 1
                if (dmin_down != 1) or (dmin_up != 1):
                    thermal_cluster = area + '_' + nom_cluster.replace(" ","*")
                    ensemble_dmins_etranger[thermal_cluster] = {}
                    ensemble_dmins_etranger[thermal_cluster]['dmin_up'] = dmin_up
                    ensemble_dmins_etranger[thermal_cluster]['dmin_down'] = dmin_down


    ens_cost = thermal_areas.getfloat('unserverdenergycost',"fr")
    reserve_cluster = {}
    reserve_cluster["fcr_up"] = {}
    reserve_cluster["fcr_down"] = {}
    reserve_cluster["afrr_up"] = {}
    reserve_cluster["afrr_down"] = {}
    reserve_cluster["mfrr_up"] = {}
    reserve_cluster["mfrr_down"] = {}
    reserve_cluster["new_rr_up"] = {}
    reserve_cluster["new_rr_down"] = {}


    with open(study_path +  "/input/thermal/clusters/fr/reserves.ini") as file:
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
    
    file_cost = get_ini_file(study_path + "/input/reserves/fr/reserves.ini")
    reserves_areas_cost = {}
    reserves_areas_cost["fcr_up"] = {}
    if file_cost.has_option('fcr_up','failure-cost'):
        reserves_areas_cost["fcr_up"]['failure-cost'] = file_cost.getfloat('fcr_up','failure-cost')
    else:
        reserves_areas_cost["fcr_up"]['failure-cost'] = 0
    if file_cost.has_option('fcr_up','spillage-cost'):
        reserves_areas_cost["fcr_up"]['spillage-cost'] = file_cost.getfloat('fcr_up','spillage-cost')
    else:
        reserves_areas_cost["fcr_up"]['spillage-cost'] = 0
    reserves_areas_cost["fcr_down"] = {}
    if file_cost.has_option('fcr_down','failure-cost'):
        reserves_areas_cost["fcr_down"]['failure-cost'] = file_cost.getfloat('fcr_down','failure-cost')
    else:
        reserves_areas_cost["fcr_down"]['failure-cost'] = 0
    if file_cost.has_option('fcr_down','spillage-cost'):
        reserves_areas_cost["fcr_down"]['spillage-cost'] = file_cost.getfloat('fcr_down','spillage-cost')
    else:
        reserves_areas_cost["fcr_down"]['spillage-cost'] = 0
    reserves_areas_cost["afrr_up"] = {}
    if file_cost.has_option('afrr_up','failure-cost'):
        reserves_areas_cost["afrr_up"]['failure-cost'] = file_cost.getfloat('afrr_up','failure-cost')
    else:
        reserves_areas_cost["afrr_up"]['failure-cost'] = 0
    if file_cost.has_option('afrr_up','spillage-cost'):
        reserves_areas_cost["afrr_up"]['spillage-cost'] = file_cost.getfloat('afrr_up','spillage-cost')
    else:
        reserves_areas_cost["afrr_up"]['spillage-cost'] = 0
    reserves_areas_cost["afrr_down"] = {}
    if file_cost.has_option('afrr_down','failure-cost'):
        reserves_areas_cost["afrr_down"]['failure-cost'] = file_cost.getfloat('afrr_down','failure-cost')
    else:
        reserves_areas_cost["afrr_down"]['failure-cost'] = 0
    if file_cost.has_option('afrr_down','spillage-cost'):
        reserves_areas_cost["afrr_down"]['spillage-cost'] = file_cost.getfloat('afrr_down','spillage-cost')
    else:
        reserves_areas_cost["afrr_down"]['spillage-cost'] = 0
    reserves_areas_cost["mfrr_up"] = {}
    if file_cost.has_option('mfrr_up','failure-cost'):
        reserves_areas_cost["mfrr_up"]['failure-cost'] = file_cost.getfloat('mfrr_up','failure-cost')
    else:
        reserves_areas_cost["mfrr_up"]['failure-cost'] = 0
    if file_cost.has_option('mfrr_up','spillage-cost'):
        reserves_areas_cost["mfrr_up"]['spillage-cost'] = file_cost.getfloat('mfrr_up','spillage-cost')
    else:
        reserves_areas_cost["mfrr_up"]['spillage-cost'] = 0
    reserves_areas_cost["mfrr_down"] = {}
    if file_cost.has_option('mfrr_down','failure-cost'):
        reserves_areas_cost["mfrr_down"]['failure-cost'] = file_cost.getfloat('mfrr_down','failure-cost')
    else:
        reserves_areas_cost["mfrr_down"]['failure-cost'] = 0
    if file_cost.has_option('mfrr_down','spillage-cost'):
        reserves_areas_cost["mfrr_down"]['spillage-cost'] = file_cost.getfloat('mfrr_down','spillage-cost')
    else:
        reserves_areas_cost["mfrr_down"]['spillage-cost'] = 0
    reserves_areas_cost["new_rr_up"] = {}
    if file_cost.has_option('new_rr_up','failure-cost'):
        reserves_areas_cost["new_rr_up"]['failure-cost'] = file_cost.getfloat('new_rr_up','failure-cost')
    else:
        reserves_areas_cost["new_rr_up"]['failure-cost'] = 0
    if file_cost.has_option('new_rr_up','spillage-cost'):
        reserves_areas_cost["new_rr_up"]['spillage-cost'] = file_cost.getfloat('new_rr_up','spillage-cost')
    else:
        reserves_areas_cost["new_rr_up"]['spillage-cost'] = 0
    reserves_areas_cost["new_rr_down"] = {}
    if file_cost.has_option('new_rr_down','failure-cost'):
        reserves_areas_cost["new_rr_down"]['failure-cost'] = file_cost.getfloat('new_rr_down','failure-cost')
    else:
        reserves_areas_cost["new_rr_down"]['failure-cost'] = 0
    if file_cost.has_option('new_rr_down','spillage-cost'):
        reserves_areas_cost["new_rr_down"]['spillage-cost'] = file_cost.getfloat('new_rr_down','spillage-cost')
    else:
        reserves_areas_cost["new_rr_down"]['spillage-cost'] = 0

    # reserves_areas_cost["fcr_up"]['spillage-cost'] = file_cost.getfloat('fcr_up','spillage-cost')
    # reserves_areas_cost["fcr_down"] = {}
    # reserves_areas_cost["fcr_down"]['failure-cost'] = file_cost.getfloat('fcr_down','failure-cost')
    # reserves_areas_cost["fcr_down"]['spillage-cost'] = file_cost.getfloat('fcr_down','spillage-cost')
    # reserves_areas_cost["afrr_up"] = {}
    # reserves_areas_cost["afrr_up"]['failure-cost'] = file_cost.getfloat('afrr_up','failure-cost')
    # reserves_areas_cost["afrr_up"]['spillage-cost'] = file_cost.getfloat('afrr_up','spillage-cost')
    # reserves_areas_cost["afrr_down"] = {}
    # reserves_areas_cost["afrr_down"]['failure-cost'] = file_cost.getfloat('afrr_down','failure-cost')
    # reserves_areas_cost["afrr_down"]['spillage-cost'] = file_cost.getfloat('afrr_down','spillage-cost')
    # reserves_areas_cost["mfrr_up"] = {}
    # reserves_areas_cost["mfrr_up"]['failure-cost'] = 0
    # reserves_areas_cost["mfrr_up"]['spillage-cost'] = 0
    # reserves_areas_cost["mfrr_down"] = {}
    # reserves_areas_cost["mfrr_down"]['failure-cost'] = 0
    # reserves_areas_cost["mfrr_down"]['spillage-cost'] = 0
    # reserves_areas_cost["new_rr_up"] = {}
    # reserves_areas_cost["new_rr_up"]['failure-cost'] = file_cost.getfloat('mfrr_down','failure-cost')
    # reserves_areas_cost["new_rr_up"]['spillage-cost'] = file_cost.getfloat('mfrr_down','failure-cost')
    # reserves_areas_cost["new_rr_down"] = {}
    # reserves_areas_cost["new_rr_down"]['failure-cost'] = file_cost.getfloat('mfrr_down','failure-cost')
    # reserves_areas_cost["new_rr_down"]['spillage-cost'] = file_cost.getfloat('mfrr_down','failure-cost')

    
    
    thermal_list = get_ini_file(study_path +  "/input/thermal/clusters/fr/list.ini")
    list_nom_cluster_fr = thermal_list.sections()
    list_nom_cluster_fr_enabled = []
    for nom_cluster in list_nom_cluster_fr:
        if not(thermal_list.has_option(nom_cluster,"enabled")):
            list_nom_cluster_fr_enabled.append(nom_cluster)


    ensemble_valeurs = {}

    for nom_cluster in list_nom_cluster_fr_enabled:
        thermal_cluster = 'fr_' + nom_cluster.replace(" ","*")
        ensemble_valeurs[thermal_cluster] = {}
        p_max = thermal_list.getfloat(nom_cluster,"nominalcapacity")
        ensemble_valeurs[thermal_cluster]["p_max"] =  [ p_max ] * 168
        ensemble_valeurs[thermal_cluster]["ens_cost"] =  [ ens_cost ] * 168

        if thermal_list.has_option(nom_cluster,"min-stable-power"):
            p_min = thermal_list.getfloat(nom_cluster,"min-stable-power")
            ensemble_valeurs[thermal_cluster]["p_min"] =  [ p_min ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["p_min"] = [ 0 ] * 168
        if thermal_list.has_option(nom_cluster,"min-up-time"):
            ensemble_valeurs[thermal_cluster]["dmin_up"] = thermal_list.getint(nom_cluster,"min-up-time")
        else:
            ensemble_valeurs[thermal_cluster]["dmin_up"] = 1
        if thermal_list.has_option(nom_cluster,"min-down-time"):
            ensemble_valeurs[thermal_cluster]["dmin_down"] = thermal_list.getint(nom_cluster,"min-down-time")
        else:
            ensemble_valeurs[thermal_cluster]["dmin_down"] = 1
        if thermal_list.has_option(nom_cluster,"market-bid-cost"):
            market_cost = thermal_list.getfloat(nom_cluster,"market-bid-cost")
            ensemble_valeurs[thermal_cluster]["cost"] =  [ market_cost ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["cost"] = [ 0 ] * 168
        if thermal_list.has_option(nom_cluster,"startup-cost"):
            startup_cost = thermal_list.getfloat(nom_cluster,"startup-cost")
            ensemble_valeurs[thermal_cluster]["startup_cost"] =  [ startup_cost ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["startup_cost"] = [ 0 ] * 168
        if thermal_list.has_option(nom_cluster,"fixed-cost"):
            fixed_cost = thermal_list.getfloat(nom_cluster,"fixed-cost")
            ensemble_valeurs[thermal_cluster]["fixed_cost"] =  [ fixed_cost ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["fixed_cost"] =  [ 0 ] * 168
        

        ensemble_valeurs[thermal_cluster]["primary_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost["fcr_up"]['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["primary_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost["fcr_up"]['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["primary_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost['fcr_down']['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["primary_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost['fcr_down']['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["secondary_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost['afrr_up']['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["secondary_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost['afrr_up']['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["secondary_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost['afrr_down']['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["secondary_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost['afrr_down']['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost["mfrr_up"]['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost["mfrr_up"]['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost['mfrr_down']['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost['mfrr_down']['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost["new_rr_up"]['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost["new_rr_up"]['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost['new_rr_down']['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost['new_rr_down']['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_up_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_up_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_up_off"] =  [ 0 ] * 168


        if (nom_cluster in reserve_cluster["fcr_up"]):
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_on"] = [ reserve_cluster["fcr_up"][nom_cluster]['max-power'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_up_on"] =  [ reserve_cluster["fcr_up"][nom_cluster]['participation-cost'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_on"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_up_on"] =  [ 0 ] * 168
        if (nom_cluster in reserve_cluster["fcr_down"]):
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_down"] = [ reserve_cluster["fcr_down"][nom_cluster]['max-power'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_down"] =  [ reserve_cluster["fcr_down"][nom_cluster]['participation-cost'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_down"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_down"] =  [ 0 ] * 168


        if (nom_cluster in reserve_cluster["afrr_up"]):
            ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_up_on"] = [ reserve_cluster["afrr_up"][nom_cluster]['max-power'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_up_on"] =  [ reserve_cluster["afrr_up"][nom_cluster]['participation-cost'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_up_on"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_up_on"] =  [ 0 ] * 168
        if (nom_cluster in reserve_cluster["afrr_down"]):
            ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_down"] = [ reserve_cluster["afrr_down"][nom_cluster]['max-power'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_down"] =  [ reserve_cluster["afrr_down"][nom_cluster]['participation-cost'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_down"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_down"] =  [ 0 ] * 168




        if (nom_cluster in reserve_cluster["mfrr_up"]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_on"] = [ reserve_cluster["mfrr_up"][nom_cluster]['max-power'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_on"] =  [ reserve_cluster["mfrr_up"][nom_cluster]['participation-cost'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_on"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_on"] =  [ 0 ] * 168
        if (nom_cluster in reserve_cluster["mfrr_down"]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_down"] = [ reserve_cluster["mfrr_down"][nom_cluster]['max-power'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_down"] =  [ reserve_cluster["mfrr_down"][nom_cluster]['participation-cost'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_down"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_down"] =  [ 0 ] * 168        
        if (nom_cluster in reserve_cluster["mfrr_up"]) and ('max-power-off' in reserve_cluster["mfrr_up"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_off"] =  [ reserve_cluster["mfrr_up"][nom_cluster]['max-power-off'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_off"] =  [ reserve_cluster["mfrr_up"][nom_cluster]['participation-cost-off'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_off"] =  [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_off"] =  [ 0 ] * 168


  


        if (nom_cluster in reserve_cluster["new_rr_up"]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_on"] = [ reserve_cluster["new_rr_up"][nom_cluster]['max-power'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_on"] =  [ reserve_cluster["new_rr_up"][nom_cluster]['participation-cost'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_on"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_on"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_on"] =  [ 0 ] * 168
        if (nom_cluster in reserve_cluster["new_rr_down"]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_down"] = [ reserve_cluster["new_rr_down"][nom_cluster]['max-power'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_down"] =  [ reserve_cluster["new_rr_down"][nom_cluster]['participation-cost'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_down"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary2"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_down"] =  [ 0 ] * 168
        if (nom_cluster in reserve_cluster["new_rr_up"]) and ('max-power-off' in reserve_cluster["new_rr_up"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_off"] =  [ reserve_cluster["new_rr_up"][nom_cluster]['max-power-off'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_off"] =  [ reserve_cluster["new_rr_up"][nom_cluster]['participation-cost-off'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_off"] =  [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_off"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_off"] =  [ 0 ] * 168
      
         
        ensemble_valeurs[thermal_cluster]["spillage_cost"] =  [ 0 ] * 168
        




    return(ensemble_valeurs,ensemble_dmins_etranger)


def lecture_donnees_fast(study_path):

    ensemble_valeurs = {}  

    thermal_areas = get_ini_file(study_path + "/input/thermal/areas.ini")
    list_area = thermal_areas.options('unserverdenergycost')
    list_area.append('ve_vhr_storage')
    list_area.append('y_nuc_modulation')
    list_area.append('z_batteries_pcomp')
    list_area.append('z_effacement')
    list_area.append('z_report')

    reserve_cluster = {}
    reserve_cluster["fcr_up"] = {}
    reserve_cluster["fcr_down"] = {}
    reserve_cluster["afrr_up"] = {}
    reserve_cluster["afrr_down"] = {}
    reserve_cluster["mfrr_up"] = {}
    reserve_cluster["mfrr_down"] = {}
    reserve_cluster["new_rr_up"] = {}
    reserve_cluster["new_rr_down"] = {}


    with open(study_path +  "/input/thermal/clusters/fr/reserves.ini") as file:
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




    
    for area in list_area:
        thermal_list_area = get_ini_file(study_path +  "/input/thermal/clusters/" + area + "/list.ini")
        list_nom_cluster = thermal_list_area.sections()
        for nom_cluster in list_nom_cluster:
            if not(thermal_list_area.has_option(nom_cluster,"enabled")):   
                thermal_cluster = area + '_' + nom_cluster.replace(" ","*")
                ensemble_valeurs[thermal_cluster] = {}
                p_max = thermal_list_area.getfloat(nom_cluster,"nominalcapacity")
                ensemble_valeurs[thermal_cluster]["p_max"] =  p_max

                if thermal_list_area.has_option(nom_cluster,"min-stable-power"):
                    p_min = thermal_list_area.getfloat(nom_cluster,"min-stable-power")
                    ensemble_valeurs[thermal_cluster]["p_min"] =  p_min 
                else:
                    ensemble_valeurs[thermal_cluster]["p_min"] = 0

                if thermal_list_area.has_option(nom_cluster,"min-up-time"):
                    dmin_up = thermal_list_area.getint(nom_cluster,"min-up-time")
                else:
                    dmin_up = 1
                if thermal_list_area.has_option(nom_cluster,"min-down-time"):
                    dmin_down = thermal_list_area.getint(nom_cluster,"min-down-time")
                else:
                    dmin_down = 1
                ensemble_valeurs[thermal_cluster]["dmin"] = max(dmin_down,dmin_up)
                if thermal_list_area.has_option(nom_cluster,"fixed-cost"):
                    ensemble_valeurs[thermal_cluster]["fixed_cost"] = thermal_list_area.getfloat(nom_cluster,"fixed-cost") 
                else:
                    ensemble_valeurs[thermal_cluster]["fixed_cost"] = 0  
                if thermal_list_area.has_option(nom_cluster,"startup-cost"):
                    ensemble_valeurs[thermal_cluster]["startup_cost"] =  thermal_list_area.getfloat(nom_cluster,"startup-cost")
                else:
                    ensemble_valeurs[thermal_cluster]["startup_cost"] = 0
                if area == "fr":
                    ensemble_valeurs[thermal_cluster]["reserve"] = []
            

                if (nom_cluster in reserve_cluster["fcr_up"]):
                    ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_on"] =  reserve_cluster["fcr_up"][nom_cluster]['max-power'] 
                else:
                    ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_on"] =  0 
                if (nom_cluster in reserve_cluster["fcr_down"]):
                    ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_down"] =  reserve_cluster["fcr_down"][nom_cluster]['max-power'] 
                else:
                    ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_down"] =  0 

                if (nom_cluster in reserve_cluster["afrr_up"]):
                    ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_up_on"] =  reserve_cluster["afrr_up"][nom_cluster]['max-power'] 
                else:
                    ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_up_on"] = 0 
                if (nom_cluster in reserve_cluster["afrr_down"]):
                    ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_down"] =  reserve_cluster["afrr_down"][nom_cluster]['max-power'] 
                else:
                    ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_down"] =  0 

                if (nom_cluster in reserve_cluster["mfrr_up"]):
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_on"] =  reserve_cluster["mfrr_up"][nom_cluster]['max-power']
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_off"] =  reserve_cluster["mfrr_up"][nom_cluster]['max-power-off'] 
                else:
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_on"] =  0 
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_off"] =  0 
                if (nom_cluster in reserve_cluster["mfrr_down"]):
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_down"] =  reserve_cluster["mfrr_down"][nom_cluster]['max-power'] 
                else:
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_down"] =  0 

                if (nom_cluster in reserve_cluster["new_rr_up"]):
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_on"] =  reserve_cluster["new_rr_up"][nom_cluster]['max-power'] 
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_off"] =  reserve_cluster["new_rr_up"][nom_cluster]['max-power-off']
                else:
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_on"] =  0 
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_off"] =  0 
                if (nom_cluster in reserve_cluster["new_rr_down"]):
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_down"] =  reserve_cluster["new_rr_down"][nom_cluster]['max-power'] 
                else:
                    ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_down"] =  0 





    
    with open(study_path +  "/input/thermal/clusters/fr/reserves.ini") as file:
        liste_reserves_cluster = file.read().split("[")
        for bloc_reserve in range(1,len(liste_reserves_cluster)):
            lignes = liste_reserves_cluster[bloc_reserve].split("\n")
            reserve = lignes[0].split("]")[0]
            cluster = lignes[1].split(" = ")[1]
            thermal_cluster = 'fr_' + cluster.replace(" ","*")
            ensemble_valeurs[thermal_cluster]["reserve"].append(reserve)


    return(ensemble_valeurs)


# def heuristique_dmin_accurate(dictionnaire_valeur,list_nbr_min,problem_opti : OptimizationProblem):
    
#     nb_units_min = pd.DataFrame(
#         np.transpose([list_nbr_min[t] for t in range(168)]),
#         index=[i for i in range(168)],
#     )
#     nb_units_max = pd.DataFrame(
#         np.transpose(dictionnaire_valeur["nb_units_max"]),
#         index=[i for i in range(168)],
#     )


#     database = DataBase()
#     thermal_cluster = "test_cluster"

#     database.add_data(thermal_cluster, "d_min_up", ConstantData(dictionnaire_valeur["dmin_up"]))
#     database.add_data(thermal_cluster, "d_min_down", ConstantData(dictionnaire_valeur["dmin_down"]))
#     database.add_data(thermal_cluster, "nb_units_max", TimeScenarioSeriesData(nb_units_max))
#     database.add_data(thermal_cluster, "nb_units_min", TimeScenarioSeriesData(nb_units_min))


#     nb_units_max_min_down_time = get_max_unit_for_min_down_time(dictionnaire_valeur["dmin_down"],nb_units_max,168)
#     database.add_data(thermal_cluster, "nb_units_max_min_down_time", TimeScenarioSeriesData(nb_units_max_min_down_time))

#     max_failure = get_max_failures(nb_units_max,168)
#     database.add_data(thermal_cluster, "max_failure", TimeScenarioSeriesData(max_failure))


#     if problem_opti == None:

#         thermal_problem_builder = ThermalProblemBuilder(
#         network=Network("test"),
#         database=database,
#         time_scenario_hour_parameter=TimeScenarioHourParameter(0, 0, 168),
#     )

#         problem_opti = (
#             thermal_problem_builder.heuristic_resolution_step(
#                 BlockScenarioIndex(0, 0),
#                 id_component=thermal_cluster,
#                 model=THERMAL_CLUSTER_HEURISTIQUE_DMIN,
#             )
#         )
#     else:
#         cluster = create_component(model=THERMAL_CLUSTER_HEURISTIQUE_DMIN, id=thermal_cluster)

#         network = Network("test")
#         network.add_component(cluster)

#         database.requirements_consistency(network)

#         opt_context = OptimizationContext(
#             network, 
#             database, 
#             TimeBlock(1, timesteps(BlockScenarioIndex(0, 0), TimeScenarioHourParameter(0, 0, 168))), 
#             [BlockScenarioIndex(0, 0).scenario], 
#             border_management= BlockBorderManagement.CYCLE
#         )
#         problem_opti.context = opt_context



#     # resolution_step_accurate_heuristic.solver.EnableOutput()
#     status = problem_opti.solver.Solve()
#     assert status == pywraplp.Solver.OPTIMAL

#     return(OutputValues(problem_opti)._components[thermal_cluster]._variables['nb_on'].value[0],problem_opti)



def heuristique_dmin_accurate_long(dictionnaire_valeur,list_nbr_min):
    

    nb_units_min = pd.DataFrame(
        np.transpose([list_nbr_min[t] for t in range(168)]),
        index=[i for i in range(168)],
    )
    nb_units_max = pd.DataFrame(
        np.transpose(dictionnaire_valeur["nb_units_max"]),
        index=[i for i in range(168)],
    )


    database = DataBase()
    thermal_cluster = "test_cluster"

    database.add_data(thermal_cluster, "d_min_up", ConstantData(dictionnaire_valeur["dmin_up"]))
    database.add_data(thermal_cluster, "d_min_down", ConstantData(dictionnaire_valeur["dmin_down"]))
    database.add_data(thermal_cluster, "nb_units_max", TimeScenarioSeriesData(nb_units_max))
    database.add_data(thermal_cluster, "nb_units_min", TimeScenarioSeriesData(nb_units_min))


    nb_units_max_min_down_time = get_max_unit_for_min_down_time(dictionnaire_valeur["dmin_down"],nb_units_max,168)
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


    # resolution_step_accurate_heuristic.solver.EnableOutput()
    status = resolution_step_accurate_heuristic.solver.Solve()
    assert status == pywraplp.Solver.OPTIMAL

    return(OutputValues(resolution_step_accurate_heuristic)._components[thermal_cluster]._variables['nb_on'].value[0])


def heuristique_dmin_fast(dmin,list_nbr_min):
    
    nbr_ajout = [0] * dmin
    nbr_final = [ [0] * 168 for t in range(dmin) ]
    nbr_block = 168 // dmin - 1
    taille_petit_block = 168 % dmin
    
    for heure_depart in range(dmin):
        block_ajust = list(range(0,heure_depart)) + list(range(168 - dmin + heure_depart,168))
        nbr_max_block_ajust = max(list_nbr_min[0:heure_depart] + list_nbr_min[168 - dmin + heure_depart:168])
        for j in block_ajust:
                nbr_ajout[heure_depart] += nbr_max_block_ajust - list_nbr_min[j] 
                nbr_final[heure_depart][j] = nbr_max_block_ajust
        for i in range(nbr_block):
            nbr_max_block = max(list_nbr_min[(i * dmin + heure_depart):((i+1) * dmin + heure_depart)])
            for j in range(dmin):
                nbr_ajout[heure_depart] += nbr_max_block - list_nbr_min[i * dmin + heure_depart + j] 
                nbr_final[heure_depart][i * dmin + heure_depart + j] = nbr_max_block
        if taille_petit_block !=0:
            nbr_max_petit_block = max(list_nbr_min[(nbr_block * dmin + heure_depart):(nbr_block * dmin + heure_depart + taille_petit_block)])
            for j in range(taille_petit_block):
                    nbr_ajout[heure_depart] += nbr_max_petit_block - list_nbr_min[nbr_block * dmin + heure_depart + j] 
                    nbr_final[heure_depart][nbr_block * dmin + heure_depart + j] = nbr_max_petit_block

    return(nbr_final[nbr_ajout.index(min(nbr_ajout))])




def BP_week_accurate(output_path,ensemble_valeur_annuel,ensemble_dmins_etranger,week,bases):

    temps_initial = time.perf_counter()

    m = read_mps(output_path,505,week,"XPRESS_LP")
    
    
    temps_post_read_mps = time.perf_counter()

    var = m.variables()
    contraintes = m.constraints()
    delete_constraint(contraintes, 168*3, 'POffUnitsLowerBound::area<fr>:')


    list_cluster_eteint = ["FR_CCGT*new","FR_DSR_industrie","FR_Hard*coal*new","FR_Light*oil"]
    list_pmax_eteint = [452,36,586.7,135.8]
    for i in range(4):
        cluster = list_cluster_eteint[i]
        pmax = list_pmax_eteint[i]
        nom_poff_mfrr= "ParticipationOfOffUnitsToReserve::area<fr>::ThermalCluster<" + cluster + ">::Reserve<mfrr_up>::hour<"
        list_poff_mfrr = [ var[c] for c in range(len(var)) if nom_poff_mfrr in var[c].name()]
        nom_poff_rr= "ParticipationOfOffUnitsToReserve::area<fr>::ThermalCluster<" + cluster + ">::Reserve<new_rr_up>::hour<"
        list_poff_rr = [ var[c] for c in range(len(var)) if nom_poff_rr in var[c].name()]
        nom_nodu= "NODU::area<fr>::ThermalCluster<" + cluster + ">::hour<"
        list_nodu = [ var[c] for c in range(len(var)) if nom_nodu in var[c].name()]
        for t in range(168):
            poff_mfrr = list_poff_mfrr[t]
            poff_rr = list_poff_rr[t]
            nodu = list_nodu[t]
            mbarre = nodu.ub()
            borne = pmax * mbarre
            nom_contrainte = "NouvelleContrainteEteinte::area<fr>::ThermalCluster<" + cluster + ">::hour<" + str(t) + ">"
            m.Add(
                    poff_mfrr
                    + poff_rr
                    + pmax * nodu
                    <= borne,
                    name=nom_contrainte,
                )
        

    # lp_format = m.ExportModelAsLpFormat(False)
    # with open("model.lp","w") as file:
    #     file.write(lp_format)

    temps_pre_opti1 = time.perf_counter()

    # if bases != None:
    #     load_basis(m,bases)

    temps_load_bases = time.perf_counter()

    solve_complete_problem(m)
    cost1 = m.Objective().Value()
    
    temps_post_opti1 = time.perf_counter()

    bases = get_basis(m)

    temps_get_bases = time.perf_counter()


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
    
    temps_lecture_resultat = time.perf_counter()

    list_thermal_clusters = thermal_var_production.cluster_name.unique()

    list_cluster_fr = []
    for thermal_cluster in list_thermal_clusters:
        [nom_noeud,nom_cluster] = thermal_cluster.split("_",1)
        if nom_noeud == "fr":
            list_cluster_fr.append(thermal_cluster)

    ensemble_valeur_semaine = {}

    for thermal_cluster in list_cluster_fr:
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

        


    temps_ensemble_valeur_semaine_fr = time.perf_counter()

    for thermal_cluster in list_cluster_fr: 
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
        de_accurate_base.to_csv("result_step1_" + thermal_cluster.replace("*","_") + ".csv",index=False)

    



    nbr_heuristique = {}
    nbr_on_final = {}


    for thermal_cluster in list_thermal_clusters:
        if not(thermal_cluster in list_cluster_fr):
            nbr_on_post_optim = round(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"],6)
            nbr_heuristique[thermal_cluster] = list(np.ceil(nbr_on_post_optim))

    temps_heuristique_arrondi_etranger = time.perf_counter()

    for thermal_cluster in list_thermal_clusters:
        if not(thermal_cluster in list_cluster_fr):
            if (thermal_cluster in ensemble_dmins_etranger) and (nbr_heuristique[thermal_cluster] != list([float(0)] * 168)):
                ensemble_dmins_etranger[thermal_cluster]["nb_units_max"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["ub"])
                nbr_on_final[thermal_cluster] = heuristique_dmin_accurate_long(ensemble_dmins_etranger[thermal_cluster],nbr_heuristique[thermal_cluster])
            else:
                nbr_on_final[thermal_cluster] = nbr_heuristique[thermal_cluster]

    temps_heuristique_dmin_etranger = time.perf_counter()


    for thermal_cluster in list_thermal_clusters:
        if not(thermal_cluster in list_cluster_fr):
            id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
            for hour, id in enumerate(id_var):
                change_lower_bound(var,id,nbr_on_final[thermal_cluster][hour])
                change_upper_bound(var,id,nbr_on_final[thermal_cluster][hour])

    temps_changement_borne_etranger = time.perf_counter()




    for thermal_cluster in list_cluster_fr:
        ensemble_valeurs = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]

        heuristique_resultat = old_heuristique(
            [t for t in range(168)],
            ensemble_valeurs,
            # "perte",    # version
            # "choix", # option
            # "réduction", # bonus
            )
        
        nbr_heuristique[thermal_cluster] = []
        for t in range(168):
            nbr_heuristique[thermal_cluster].append(heuristique_resultat[t][0])
    
    temps_heuristique_arrondi_fr_old = time.perf_counter()

    for thermal_cluster in list_cluster_fr:
        ensemble_valeurs = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]
        if ((ensemble_valeurs["dmin_up"] == 1) and (ensemble_valeurs["dmin_down"] == 1)) or (nbr_heuristique[thermal_cluster] == list([nbr_heuristique[thermal_cluster][0]] * 168)):
            nbr_on_final[thermal_cluster] = nbr_heuristique[thermal_cluster]
        else:
            nbr_on_final[thermal_cluster] = heuristique_dmin_accurate_long(ensemble_valeurs,nbr_heuristique[thermal_cluster])

    temps_heuristique_dmin_fr_old = time.perf_counter()


    for thermal_cluster in list_cluster_fr:
        id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
        for hour, id in enumerate(id_var):
            change_lower_bound(var,id,ceil(nbr_on_final[thermal_cluster][hour]))
            change_upper_bound(var,id,ceil(nbr_on_final[thermal_cluster][hour]))
    
    temps_changement_borne_fr_old = time.perf_counter()

    # de_accurate_heuristique = pd.DataFrame(data = nbr_heuristique)
    # de_accurate_heuristique.to_csv("result_mps_heuristique_old.csv",index=False)



    solve_complete_problem(m)
 
    cost_old = m.Objective().Value()

    temps_post_opti2_old = time.perf_counter()

    heure_defaillance_old = [0] * 9
    quantite_defaillance_old = [0] * 9
    for i in range(len(var)):
        var_name = var[i].name()
        quantite = var[i].solution_value()
        if "PositiveUnsuppliedEnergy::area<fr>:" in var_name:
            defaillance_prod = quantite
            if defaillance_prod > 0:
                heure_defaillance_old[0] += 1
                quantite_defaillance_old[0] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<fcr_up>:" in var_name:
            defaillance_fcr_up = quantite
            if defaillance_fcr_up > 0:
                heure_defaillance_old[1] += 1
                quantite_defaillance_old[1] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<fcr_down>:" in var_name:
            defaillance_fcr_down = quantite
            if defaillance_fcr_down > 0:
                heure_defaillance_old[2] += 1
                quantite_defaillance_old[2] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<afrr_up>:" in var_name:
            defaillance_afrr_up = quantite
            if defaillance_afrr_up > 0:
                heure_defaillance_old[3] += 1
                quantite_defaillance_old[3] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<afrr_down>:" in var_name:
            defaillance_afrr_down = quantite
            if defaillance_afrr_down > 0:
                heure_defaillance_old[4] += 1
                quantite_defaillance_old[4] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<mfrr_up>:" in var_name:
            defaillance_mfrr_up = quantite
            if defaillance_mfrr_up > 0:
                heure_defaillance_old[5] += 1
                quantite_defaillance_old[5] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<mfrr_down>:" in var_name:
            defaillance_mfrr_down = quantite
            if defaillance_mfrr_down > 0:
                heure_defaillance_old[6] += 1
                quantite_defaillance_old[6] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<new_rr_up>:" in var_name:
            defaillance_rr_up = quantite
            if defaillance_rr_up > 0:
                heure_defaillance_old[7] += 1
                quantite_defaillance_old[7] += quantite
        if "InternalUnsatisfiedReserve::area<fr>::Reserve<new_rr_down>:" in var_name:
            defaillance_rr_down = quantite
            if defaillance_rr_down > 0:
                heure_defaillance_old[8] += 1
                quantite_defaillance_old[8] += quantite
    
    load_basis(m,bases)

    temps_post_defaillace_old = time.perf_counter()




    for thermal_cluster in list_cluster_fr:
        ensemble_valeurs = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]

        heuristique_resultat = heuristique_opti_repartition_sans_pmin(
            [t for t in range(168)],
            ensemble_valeurs,
            "choix",    # version
            # "choix", # option
            # "réduction", # bonus
            )
        
        nbr_heuristique[thermal_cluster] = []
        for t in range(168):
            nbr_heuristique[thermal_cluster].append(heuristique_resultat[t][0])
    
    temps_heuristique_arrondi_fr_new = time.perf_counter()

    for thermal_cluster in list_cluster_fr:
        ensemble_valeurs = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]
        if ((ensemble_valeurs["dmin_up"] == 1) and (ensemble_valeurs["dmin_down"] == 1)) or (nbr_heuristique[thermal_cluster] == list([nbr_heuristique[thermal_cluster][0]] * 168)):
            nbr_on_final[thermal_cluster] = nbr_heuristique[thermal_cluster]
        else:
            nbr_on_final[thermal_cluster] = heuristique_dmin_accurate_long(ensemble_valeurs,nbr_heuristique[thermal_cluster],)

    temps_heuristique_dmin_fr_new = time.perf_counter()


    for thermal_cluster in list_cluster_fr:
        id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
        for hour, id in enumerate(id_var):
            change_lower_bound(var,id,ceil(nbr_on_final[thermal_cluster][hour]))
            change_upper_bound(var,id,ceil(nbr_on_final[thermal_cluster][hour]))
    
    temps_changement_borne_fr_new = time.perf_counter()

    # de_accurate_heuristique = pd.DataFrame(data = nbr_heuristique)
    # de_accurate_heuristique.to_csv("result_mps_heuristique_new.csv",index=False)



    solve_complete_problem(m)
    cost_new = m.Objective().Value()

    temps_post_opti2_new = time.perf_counter()

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


    cost = [cost1,cost_old,cost_new]
    temps = [temps_post_read_mps-temps_initial,
             temps_pre_opti1 - temps_post_read_mps,
             temps_load_bases-temps_pre_opti1,
             temps_post_opti1-temps_load_bases,
             temps_get_bases-temps_post_opti1,
             temps_lecture_resultat-temps_get_bases,
             temps_ensemble_valeur_semaine_fr-temps_lecture_resultat,
             temps_heuristique_arrondi_etranger -temps_ensemble_valeur_semaine_fr,
             temps_heuristique_dmin_etranger - temps_heuristique_arrondi_etranger,
             temps_changement_borne_etranger-temps_heuristique_dmin_etranger,
             temps_heuristique_arrondi_fr_old -temps_changement_borne_etranger,
             temps_heuristique_dmin_fr_old - temps_heuristique_arrondi_fr_old,
             temps_changement_borne_fr_old - temps_heuristique_dmin_fr_old,
             temps_post_opti2_old-temps_changement_borne_fr_old,
             temps_heuristique_arrondi_fr_new -temps_post_defaillace_old,
             temps_heuristique_dmin_fr_new - temps_heuristique_arrondi_fr_new,
             temps_changement_borne_fr_new-temps_heuristique_dmin_fr_new,
             temps_post_opti2_new-temps_changement_borne_fr_new
             ]
    
    
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

    ensemble_valeur = {}
    for thermal_cluster in list_cluster_fr:
        ensemble_valeurs[thermal_cluster] = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]
        ensemble_valeurs[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["nb_on"] = list(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])
        
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_primary_reserve_up_on"][0] != 0:
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_fcr_up_on.loc[thermal_var_fcr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_primary_reserve_down"][0] != 0:
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_fcr_down_on.loc[thermal_var_fcr_down_on["cluster_name"]==thermal_cluster]["sol"])


        if ensemble_valeur_annuel[thermal_cluster]["participation_max_secondary_reserve_up_on"][0] != 0:
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"] = list(thermal_var_afrr_up_on.loc[thermal_var_afrr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_secondary_reserve_down"][0] != 0:
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"] = list(thermal_var_afrr_down_on.loc[thermal_var_afrr_down_on["cluster_name"]==thermal_cluster]["sol"])


        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_up_on"][0] != 0:
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_mfrr_up_on.loc[thermal_var_mfrr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_down"][0] != 0:
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"] = list(thermal_var_mfrr_down_on.loc[thermal_var_mfrr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_up_off"][0] != 0:
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_mfrr_up_off.loc[thermal_var_mfrr_up_off["cluster_name"]==thermal_cluster]["sol"])


        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_up_on"][0] != 0:
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_on"] = list(thermal_var_new_rr_up_on.loc[thermal_var_new_rr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_down"][0] != 0:
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary2"] = list(thermal_var_new_rr_down_on.loc[thermal_var_new_rr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_up_off"][0] != 0:
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_off"] = list(thermal_var_new_rr_up_off.loc[thermal_var_new_rr_up_off["cluster_name"]==thermal_cluster]["sol"])

        de_accurate_peak = pd.DataFrame(data = {"energy_generation":ensemble_valeurs[thermal_cluster]["energy_generation"],
                                                "nodu":ensemble_valeurs[thermal_cluster]["nb_on"],
                                                "generation_reserve_up_primary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"],
                                                "generation_reserve_down_primary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"],
                                                "generation_reserve_up_secondary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"],
                                                "generation_reserve_down_secondary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"],
                                                "generation_reserve_up_tertiary1_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"],
                                                "generation_reserve_down_tertiary1":ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"],
                                                "generation_reserve_up_tertiary1_off":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"],
                                                "generation_reserve_up_tertiary2_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_on"],
                                                "generation_reserve_down_tertiary2":ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary2"],
                                                "generation_reserve_up_tertiary2_off":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_off"]})
        de_accurate_peak.to_csv("result_step2" + thermal_cluster.replace("*","_") + ".csv",index=False)

    return (cost,temps,heure_defaillance_old,quantite_defaillance_old,heure_defaillance,quantite_defaillance,bases)



def BP_week_milp(output_path,week):





    temps_initial = time.perf_counter()

    m = read_mps(output_path,505,week,"XPRESS")

      
    
    temps_post_read_mps = time.perf_counter()

    contraintes = m.constraints()
    var = m.variables()
    # delete_constraint(contraintes, 168*3, 'POffUnitsLowerBound::area<fr>:')

    list_cluster_eteint = ["FR_CCGT*new","FR_DSR_industrie","FR_Hard*coal*new","FR_Light*oil"]
    list_pmax_eteint = [452,36,586.7,135.8]
    for i in range(4):
        cluster = list_cluster_eteint[i]
        pmax = list_pmax_eteint[i]
        nom_poff_mfrr= "ParticipationOfOffUnitsToReserve::area<fr>::ThermalCluster<" + cluster + ">::Reserve<mfrr_up>::hour<"
        list_poff_mfrr = [ var[c] for c in range(len(var)) if nom_poff_mfrr in var[c].name()]
        nom_poff_rr= "ParticipationOfOffUnitsToReserve::area<fr>::ThermalCluster<" + cluster + ">::Reserve<new_rr_up>::hour<"
        list_poff_rr = [ var[c] for c in range(len(var)) if nom_poff_rr in var[c].name()]
        nom_nodu= "NODU::area<fr>::ThermalCluster<" + cluster + ">::hour<"
        list_nodu = [ var[c] for c in range(len(var)) if nom_nodu in var[c].name()]
        for t in range(168):
            poff_mfrr = list_poff_mfrr[t]
            poff_rr = list_poff_rr[t]
            nodu = list_nodu[t]
            mbarre = nodu.ub()
            borne = pmax * mbarre
            nom_contrainte = "NouvelleContrainteEteinte::area<fr>::ThermalCluster<" + cluster + ">::hour<" + str(t) + ">"
            m.Add(
                    poff_mfrr
                    + poff_rr
                    + pmax * nodu
                    <= borne,
                    name=nom_contrainte,
                )




    milp_version(m)

    interger_vars = [
        i
        for i in range(len(var))
        if var[i].name().strip().split("::")[0]
        in [
            "NumberOfOffUnitsParticipatingToReserve",
        ]
    ]
    for i in interger_vars:
        var[i].SetInteger(True)


    # lp_format = m.ExportModelAsLpFormat(False)
    # with open("model_milp_pmin.lp","w") as file:
    #     file.write(lp_format)  


    
    temps_conversion_milp = time.perf_counter()

    solve_complete_problem(m)

    cost = m.Objective().Value()

    temps_post_optim = time.perf_counter()

    

    thermal_var_nodu = find_var(var,["NODU"])[0]

    list_thermal_clusters = thermal_var_nodu.cluster_name.unique()

    list_cluster_fr = []
    for thermal_cluster in list_thermal_clusters:
        [nom_noeud,nom_cluster] = thermal_cluster.split("_",1)
        if nom_noeud == "fr":
            list_cluster_fr.append(thermal_cluster)


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

    # (thermal_var_production,thermal_var_nodu,thermal_var_reserves_on,thermal_var_reserves_off,thermal_var_nodu_off) = find_var(var,["DispatchableProduction","NODU","ParticipationOfRunningUnitsToReserve","ParticipationOfOffUnitsToReserve","NumberOfOffUnitsParticipatingToReserve"])
    # thermal_var_fcr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_up"]
    # thermal_var_fcr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_down"]
    # thermal_var_afrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_up"]
    # thermal_var_afrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_down"]
    # thermal_var_mfrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_up"]
    # thermal_var_mfrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_down"]
    # thermal_var_mfrr_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="mfrr_up"]
    # thermal_var_new_rr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="new_rr_up"]
    # thermal_var_new_rr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="new_rr_down"]
    # thermal_var_new_rr_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="new_rr_up"]
    # thermal_var_nodu_off_mfrr=thermal_var_nodu_off.loc[thermal_var_nodu_off["reserve_name"]=="mfrr_up"]
    # thermal_var_nodu_off_rr=thermal_var_nodu_off.loc[thermal_var_nodu_off["reserve_name"]=="new_rr_up"]

    # ensemble_valeurs = {}
    # for nom_thermal_cluster in list_cluster_eteint:
    #     thermal_cluster = "fr_" + nom_thermal_cluster
    #     ensemble_valeurs[thermal_cluster] = {}
    #     ensemble_valeurs[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeurs[thermal_cluster]["nb_on"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeurs[thermal_cluster]["nb_off_mfrr"] = list(thermal_var_nodu_off_mfrr.loc[thermal_var_nodu_off_mfrr["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeurs[thermal_cluster]["nb_off_rr"] = list(thermal_var_nodu_off_rr.loc[thermal_var_nodu_off_rr["cluster_name"]==thermal_cluster]["sol"])
        
    #     ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_fcr_up_on.loc[thermal_var_fcr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_fcr_down_on.loc[thermal_var_fcr_down_on["cluster_name"]==thermal_cluster]["sol"])


    #     ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"] = list(thermal_var_afrr_up_on.loc[thermal_var_afrr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"] = list(thermal_var_afrr_down_on.loc[thermal_var_afrr_down_on["cluster_name"]==thermal_cluster]["sol"])


    #     ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_mfrr_up_on.loc[thermal_var_mfrr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"] = list(thermal_var_mfrr_down_on.loc[thermal_var_mfrr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_mfrr_up_off.loc[thermal_var_mfrr_up_off["cluster_name"]==thermal_cluster]["sol"])


    #     ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_on"] = list(thermal_var_new_rr_up_on.loc[thermal_var_new_rr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary2"] = list(thermal_var_new_rr_down_on.loc[thermal_var_new_rr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_off"] = list(thermal_var_new_rr_up_off.loc[thermal_var_new_rr_up_off["cluster_name"]==thermal_cluster]["sol"])

    #     de_accurate_peak = pd.DataFrame(data = {"energy_generation":ensemble_valeurs[thermal_cluster]["energy_generation"],
    #                                             "nodu":ensemble_valeurs[thermal_cluster]["nb_on"],
    #                                             "nb_off_mfrr":ensemble_valeurs[thermal_cluster]["nb_off_mfrr"],
    #                                             "nb_off_rr":ensemble_valeurs[thermal_cluster]["nb_off_rr"],
    #                                             "generation_reserve_up_primary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"],
    #                                             "generation_reserve_down_primary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"],
    #                                             "generation_reserve_up_secondary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"],
    #                                             "generation_reserve_down_secondary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"],
    #                                             "generation_reserve_up_tertiary1_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"],
    #                                             "generation_reserve_down_tertiary1":ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"],
    #                                             "generation_reserve_up_tertiary1_off":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"],
    #                                             "generation_reserve_up_tertiary2_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_on"],
    #                                             "generation_reserve_down_tertiary2":ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary2"],
    #                                             "generation_reserve_up_tertiary2_off":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_off"]})
    #     de_accurate_peak.to_csv("result_step_milp_" + thermal_cluster.replace("*","_") + ".csv",index=False)



    # data = {}
    # for thermal_cluster in list_cluster_fr: 
    #     data[thermal_cluster] = list(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])
    # de_accurate_base = pd.DataFrame(data)
    # de_accurate_base.to_csv("result_milp_pmin.csv",index=False)

    temps = [temps_post_read_mps-temps_initial,
             temps_conversion_milp-temps_post_read_mps,
             temps_post_optim-temps_conversion_milp,
    ]

    return (cost,temps,heure_defaillance,quantite_defaillance)




def BP_week_fast_eteint(output_path,ensemble_valeur_annuel,week,bases):

    temps_initial = time.perf_counter()

    m = read_mps(output_path,505,week,"XPRESS_LP")

    temps_post_read_mps = time.perf_counter()
    

    var = m.variables()
    contraintes = m.constraints()
    thermal_var_nodu = find_var(var,["NODU"])[0]
    list_thermal_clusters = thermal_var_nodu.cluster_name.unique()
    nbr_thermal_clusters = len(list_thermal_clusters)


    list_cluster_fr = []
    for thermal_cluster in list_thermal_clusters:
        nom_noeud= thermal_cluster.split("_",1)[0]
        if nom_noeud == "fr":
            list_cluster_fr.append(thermal_cluster)


    delete_constraint(contraintes, 168*3, 'POffUnitsLowerBound::area<fr>:')  #il y a 3 clusters avec de l'éteint
    
    delete_variable(var,m,168*nbr_thermal_clusters,'NumberStartingDispatchableUnits::area<')
    delete_variable(var,m,168*nbr_thermal_clusters,'NumberStoppingDispatchableUnits::area<')
    delete_variable(var,m,168*nbr_thermal_clusters,'NumberBreakingDownDispatchableUnits::area<')
    
    delete_constraint(contraintes,168*nbr_thermal_clusters,'NbDispUnitsMinBoundSinceMinUpTime::area<')
    delete_constraint(contraintes,168*nbr_thermal_clusters,'NbUnitsOutageLessThanNbUnitsStop::area<')
    delete_constraint(contraintes,168*nbr_thermal_clusters,'MinDownTime::area<')
    delete_constraint(contraintes,168*nbr_thermal_clusters,'ConsistenceNODU::area<')
    delete_constraint(contraintes,168*nbr_thermal_clusters,'PMaxDispatchableGeneration::area<')
    delete_constraint(contraintes,168*nbr_thermal_clusters,'PMinDispatchableGeneration::area<')

    list_cluster_eteint = ["FR_CCGT*new","FR_DSR_industrie","FR_Hard*coal*new","FR_Light*oil"]
    list_pmax_eteint = [452,36,586.7,135.8]
    for i in range(4):
        cluster = list_cluster_eteint[i]
        pmax = list_pmax_eteint[i]
        nom_poff_mfrr= "ParticipationOfOffUnitsToReserve::area<fr>::ThermalCluster<" + cluster + ">::Reserve<mfrr_up>::hour<"
        list_poff_mfrr = [ var[c] for c in range(len(var)) if nom_poff_mfrr in var[c].name()]
        nom_poff_rr= "ParticipationOfOffUnitsToReserve::area<fr>::ThermalCluster<" + cluster + ">::Reserve<new_rr_up>::hour<"
        list_poff_rr = [ var[c] for c in range(len(var)) if nom_poff_rr in var[c].name()]
        nom_nodu= "NODU::area<fr>::ThermalCluster<" + cluster + ">::hour<"
        list_nodu = [ var[c] for c in range(len(var)) if nom_nodu in var[c].name()]
        for t in range(168):
            poff_mfrr = list_poff_mfrr[t]
            poff_rr = list_poff_rr[t]
            nodu = list_nodu[t]
            mbarre = nodu.ub()
            borne = pmax * mbarre
            nom_contrainte = "NouvelleContrainteEteinte::area<fr>::ThermalCluster<" + cluster + ">::hour<" + str(t) + ">"
            m.Add(
                    poff_mfrr
                    + poff_rr
                    + pmax * nodu
                    <= borne,
                    name=nom_contrainte,
                )

    # list_cluster_fr_reserve = []
    # nbr_reserve_x_cluster = 0
    # nbr_cluster_avec_reserve = 0
    # for thermal_cluster in list_cluster_fr:
    #     if len(ensemble_valeur_annuel[thermal_cluster]["reserve"]) != 0:
    #         list_cluster_fr_reserve.append(thermal_cluster)
    #         nbr_cluster_avec_reserve += 1
    #         nbr_reserve_x_cluster += len(ensemble_valeur_annuel[thermal_cluster]["reserve"])

    # delete_constraint(contraintes,168*nbr_cluster_avec_reserve,'POutCapacityThreasholdInf::area<')
    # delete_constraint(contraintes,168*nbr_cluster_avec_reserve,'POutCapacityThreasholdSup::area<')

    # delete_constraint(contraintes,168*nbr_reserve_x_cluster,'PMaxReserve::area<')

    var_id = [i for i in range(len(var)) if 'NODU::area<' in var[i].name()]
    assert len(var_id) in [0, 168*nbr_thermal_clusters]
    if len(var_id) == 168*nbr_thermal_clusters:
        for i in var_id:
            m.Objective().SetCoefficient(var[i], 0)


    temps_conversion_fast = time.perf_counter()


    lp_format = m.ExportModelAsLpFormat(False)
    with open("model_fast_sans_pmin.lp","w") as file:
        file.write(lp_format)    

    # if bases != None:
    #     load_basis(m,bases)

    temps_load_bases = time.perf_counter()

    solve_complete_problem(m)

    cost1 = m.Objective().Value()


    temps_post_opti1 = time.perf_counter()

    bases = get_basis(m)
    # a = m.Iterations()

    temps_get_bases = time.perf_counter()

    (thermal_var_production,thermal_var_nodu,thermal_var_reserves_on,thermal_var_reserves_off,thermal_var_nodu_off) = find_var(var,["DispatchableProduction","NODU","ParticipationOfRunningUnitsToReserve","ParticipationOfOffUnitsToReserve","NumberOfOffUnitsParticipatingToReserve"])
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
    thermal_var_nodu_off_mfrr=thermal_var_nodu_off.loc[thermal_var_nodu_off["reserve_name"]=="mfrr_up"]
    thermal_var_nodu_off_rr=thermal_var_nodu_off.loc[thermal_var_nodu_off["reserve_name"]=="new_rr_up"]
    
    temps_lecture_resultat = time.perf_counter()

    list_thermal_clusters = thermal_var_production.cluster_name.unique()


    ensemble_valeur_semaine = {}

    for thermal_cluster in list_thermal_clusters:
        ensemble_valeur_semaine[thermal_cluster] = {}
        ensemble_valeur_semaine[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeur_semaine[thermal_cluster]["max_generating"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["ub"])
        ensemble_valeur_semaine[thermal_cluster]["min_generating"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["lb"])
        
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_fcr_up_on.loc[thermal_var_fcr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_fcr_down_on.loc[thermal_var_fcr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] = [0]* 168

        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] = list(thermal_var_afrr_up_on.loc[thermal_var_afrr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] = list(thermal_var_afrr_down_on.loc[thermal_var_afrr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] = [0]* 168

        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_mfrr_up_on.loc[thermal_var_mfrr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_mfrr_up_off.loc[thermal_var_mfrr_up_off["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeur_semaine[thermal_cluster]["nb_off_mfrr"] = list(thermal_var_nodu_off_mfrr.loc[thermal_var_nodu_off_mfrr["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] = [0]* 168
            ensemble_valeur_semaine[thermal_cluster]["nb_off_mfrr"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] = list(thermal_var_mfrr_down_on.loc[thermal_var_mfrr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] = [0]* 168

        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] = list(thermal_var_new_rr_up_on.loc[thermal_var_new_rr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"] = list(thermal_var_new_rr_up_off.loc[thermal_var_new_rr_up_off["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeur_semaine[thermal_cluster]["nb_off_rr"] = list(thermal_var_nodu_off_rr.loc[thermal_var_nodu_off_rr["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"] = [0]* 168
            ensemble_valeur_semaine[thermal_cluster]["nb_off_rr"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] = list(thermal_var_new_rr_down_on.loc[thermal_var_new_rr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] = [0]* 168

        ensemble_valeur_semaine[thermal_cluster]["nb_on"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeur_semaine[thermal_cluster]["nb_units_max"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["ub"])


    # for thermal_cluster in list_cluster_fr:
    #     de_accurate_base = pd.DataFrame(data = {
    #                                             "energy_generation":ensemble_valeur_semaine[thermal_cluster]["energy_generation"],
    #                                             "nodu":ensemble_valeur_semaine[thermal_cluster]["nb_on"],
    #                                             "generation_reserve_up_primary_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"],
    #                                             "generation_reserve_down_primary":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"],
    #                                             "generation_reserve_up_secondary_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"],
    #                                             "generation_reserve_down_secondary":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"],
    #                                             "generation_reserve_up_tertiary1_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"],
    #                                             "generation_reserve_down_tertiary1":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"],
    #                                             "generation_reserve_up_tertiary1_off":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"],
    #                                             "generation_reserve_up_tertiary2_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"],
    #                                             "generation_reserve_down_tertiary2":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"],
    #                                             "generation_reserve_up_tertiary2_off":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"],
    #                                             })
    #     de_accurate_base.to_csv("result_step1" + thermal_cluster.replace("*","_") + ".csv",index=False)

    temps_ensemble_valeur_semaine = time.perf_counter()

    nbr_guide = {}
    nbr_on_final = {}
    nbr_off = {}
    cout_nodu = 0


    for thermal_cluster in list_thermal_clusters:
        nbr_opti = [0] * 168
        for t in range(168):
            nbr_opti[t] = round(max(
                (ensemble_valeur_semaine[thermal_cluster]["energy_generation"][t] + ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"][t]+
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"][t]+ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"][t]+
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"][t]) / ensemble_valeur_annuel[thermal_cluster]["p_max"],
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_primary_reserve_up_on"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_primary_reserve_down"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_secondary_reserve_up_on"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_secondary_reserve_down"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_up_on"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_down"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_up_on"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_down"],0.0001)),                                                                       
            ),7)
        nbr_guide[thermal_cluster] = [ceil(nbr_opti[t]) for t in range(168)]

    temps_heuristique_arrondi = time.perf_counter()

    for thermal_cluster in list_thermal_clusters:
        if ensemble_valeur_annuel[thermal_cluster]['dmin'] == 1 or nbr_guide[thermal_cluster].count(nbr_guide[thermal_cluster][0]) == 168:
            nbr_on = nbr_guide[thermal_cluster]
        else:
            nbr_on = heuristique_dmin_fast(ensemble_valeur_annuel[thermal_cluster]['dmin'],nbr_guide[thermal_cluster])

        nbr_max_dispo = np.ceil(np.round(np.array(ensemble_valeur_semaine[thermal_cluster]["max_generating"]) / ensemble_valeur_annuel[thermal_cluster]["p_max"],7))
        nbr_on_final[thermal_cluster] = [min(nbr_max_dispo[t],nbr_on[t]) for t in range(168)]

    temps_heuristique_dmin = time.perf_counter()

     
    # id_contraintes_chgt_borne_inf = [ i for i in range(len(contraintes)) if 'POutBoundMin::area<' in contraintes[i].name()]
    # id_contraintes_chgt_borne_sup = [ i for i in range(len(contraintes)) if 'POutBoundMax::area<' in contraintes[i].name()]


    for thermal_cluster in list_thermal_clusters:
        [nom_noeud,nom_cluster] = thermal_cluster.split("_",1)
        puissance_minimale = [ 0 ] * 168
        puissance_maximale = [ 0 ] * 168
        for t in range(168):
            puissance_min = min((nbr_on_final[thermal_cluster][t] * ensemble_valeur_annuel[thermal_cluster]["p_min"]),ensemble_valeur_semaine[thermal_cluster]["max_generating"][t])
            puissance_minimale[t] = (max(puissance_min,ensemble_valeur_semaine[thermal_cluster]["min_generating"][t],0))
            puissance_max = min((nbr_on_final[thermal_cluster][t] * ensemble_valeur_annuel[thermal_cluster]["p_max"]),ensemble_valeur_semaine[thermal_cluster]["max_generating"][t])
            puissance_maximale[t] = (max(puissance_max,ensemble_valeur_semaine[thermal_cluster]["min_generating"][t],0))
        
        cout_nodu += nbr_on_final[thermal_cluster][0] * ensemble_valeur_annuel[thermal_cluster]["fixed_cost"]
        for t in range(1,168):
            cout_nodu += nbr_on_final[thermal_cluster][t] * ensemble_valeur_annuel[thermal_cluster]["fixed_cost"]
            if nbr_on_final[thermal_cluster][t] > nbr_on_final[thermal_cluster][t-1]:
                cout_nodu += (nbr_on_final[thermal_cluster][t]-nbr_on_final[thermal_cluster][t-1]) * ensemble_valeur_annuel[thermal_cluster]["startup_cost"]

        # nom_contrainte_cluster = '::ThermalCluster<' + nom_cluster + '>'
        # cons_id_inf = [ id_contraintes_chgt_borne_inf[i] for i in range(len(id_contraintes_chgt_borne_inf)) if nom_contrainte_cluster in contraintes[id_contraintes_chgt_borne_inf[i]].name()]
        # cons_id_sup = [ id_contraintes_chgt_borne_sup[i] for i in range(len(id_contraintes_chgt_borne_sup)) if nom_contrainte_cluster in contraintes[id_contraintes_chgt_borne_sup[i]].name()]
        
        id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
        for hour, id in enumerate(id_var):
            change_lower_bound(var,id,nbr_on_final[thermal_cluster][hour])
            change_upper_bound(var,id,nbr_on_final[thermal_cluster][hour])

        id_var = thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster,"id_var"]
        for hour, id in enumerate(id_var):
            if puissance_minimale[hour] != ensemble_valeur_semaine[thermal_cluster]["min_generating"][hour]:
                change_lower_bound(var,id,puissance_minimale[hour])
            if puissance_maximale[hour] != ensemble_valeur_semaine[thermal_cluster]["max_generating"][hour]:
                change_upper_bound(var,id,puissance_maximale[hour])
        
        nbr_off_float = [[ensemble_valeur_semaine[thermal_cluster]["nb_off_mfrr"][t],ensemble_valeur_semaine[thermal_cluster]["nb_off_rr"][t]] for t in range(168)]
        nbr_off[thermal_cluster] = []
        for t in range(168):
            nbr_on = nbr_on_final[thermal_cluster][t]
            nbr_units_max = ensemble_valeur_semaine[thermal_cluster]["nb_units_max"][t]
            nbr_off_t = [min(ceil(round(nbr_off_float[t][0],12)),nbr_units_max-nbr_on),min(ceil(round(nbr_off_float[t][1],12)),nbr_units_max-nbr_on)]
            p_min = ensemble_valeur_annuel[thermal_cluster]["p_min"]
            p_max = ensemble_valeur_annuel[thermal_cluster]["p_max"]
            participation_max_off = [ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_up_off"],ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_up_off"]]
            while sum(nbr_off_t) * p_min > p_max * (nbr_units_max - nbr_on):
                    premier_indice_non_nulle = 0
                    while nbr_off_t[premier_indice_non_nulle] == 0 :
                        premier_indice_non_nulle += 1
                    quantite_mini = participation_max_off[premier_indice_non_nulle] * min(nbr_off_float[premier_indice_non_nulle]-(nbr_off_t[premier_indice_non_nulle]-1),nbr_off_t[premier_indice_non_nulle])
                    indice_mini = premier_indice_non_nulle
                    for i in range(premier_indice_non_nulle+1,len(nbr_off_t)):
                        quantite = participation_max_off[i] * min(nbr_off_float[i]-(nbr_off_t[i]-1),nbr_off_t[i])
                        if (nbr_off_t[i] != 0) and (quantite <= quantite_mini):
                            indice_mini = i
                            quantite_mini = quantite
                    nbr_off_t[indice_mini] -= 1
            nbr_off[thermal_cluster].append(nbr_off_t) 

        # id_var = thermal_var_nodu_off_mfrr.loc[thermal_var_nodu_off_mfrr["cluster_name"]==thermal_cluster,"id_var"]
        # for hour, id in enumerate(id_var):
        #     change_lower_bound(var,id,nbr_off[thermal_cluster][hour][0])
        #     change_upper_bound(var,id,nbr_off[thermal_cluster][hour][0])
        # id_var = thermal_var_nodu_off_rr.loc[thermal_var_nodu_off_rr["cluster_name"]==thermal_cluster,"id_var"]
        # for hour, id in enumerate(id_var):
        #     change_lower_bound(var,id,nbr_off[thermal_cluster][hour][1])
        #     change_upper_bound(var,id,nbr_off[thermal_cluster][hour][1])

        # for hour, id in enumerate(cons_id_inf):
        #     if puissance_minimale[hour] != ensemble_valeur_semaine[thermal_cluster]["min_generating"][hour]:
        #         contraintes[id].SetUb( - puissance_minimale[hour])
        # for hour, id in enumerate(cons_id_sup):
        #     if puissance_maximale[hour] != ensemble_valeur_semaine[thermal_cluster]["max_generating"][hour]:
        #         contraintes[id].SetUb(puissance_maximale[hour])

    temps_changement_borne = time.perf_counter()

    lp_format = m.ExportModelAsLpFormat(False)
    with open("model_fast_2_sans_pmin.lp","w") as file:
        file.write(lp_format)


    solve_complete_problem(m)
 


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

    # de_accurate_base = pd.DataFrame(nbr_guide)
    # de_accurate_base.to_csv("nbr_guide.csv",index=False)
     

    # de_accurate_base = pd.DataFrame(nbr_on_final)
    # de_accurate_base.to_csv("nbr_on_final.csv",index=False)

    # de_accurate_base = pd.DataFrame(nbr_off)
    # de_accurate_base.to_csv("nbr_off.csv",index=False)


    # (thermal_var_production,thermal_var_nodu,thermal_var_reserves_on,thermal_var_reserves_off) = find_var(var,["DispatchableProduction","NODU","ParticipationOfRunningUnitsToReserve","ParticipationOfOffUnitsToReserve"])
    # thermal_var_fcr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_up"]
    # thermal_var_fcr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_down"]
    # thermal_var_afrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_up"]
    # thermal_var_afrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_down"]
    # thermal_var_mfrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_up"]
    # thermal_var_mfrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_down"]
    # thermal_var_mfrr_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="mfrr_up"]
    # thermal_var_new_rr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="new_rr_up"]
    # thermal_var_new_rr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="new_rr_down"]
    
    # temps_lecture_resultat = time.perf_counter()

    # list_thermal_clusters = thermal_var_production.cluster_name.unique()



    # ensemble_valeur_semaine = {}

    # for thermal_cluster in list_thermal_clusters:
    #     ensemble_valeur_semaine[thermal_cluster] = {}
    #     ensemble_valeur_semaine[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeur_semaine[thermal_cluster]["max_generating"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["ub"])
    #     ensemble_valeur_semaine[thermal_cluster]["min_generating"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["lb"])
        
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_fcr_up_on.loc[thermal_var_fcr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] = [0]* 168
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_fcr_down_on.loc[thermal_var_fcr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] = [0]* 168

    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] = list(thermal_var_afrr_up_on.loc[thermal_var_afrr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] = [0]* 168
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] = list(thermal_var_afrr_down_on.loc[thermal_var_afrr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] = [0]* 168

    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_mfrr_up_on.loc[thermal_var_mfrr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] = [0]* 168
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_mfrr_up_off.loc[thermal_var_mfrr_up_off["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] = [0]* 168
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] = list(thermal_var_mfrr_down_on.loc[thermal_var_mfrr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] = [0]* 168

    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] = list(thermal_var_new_rr_up_on.loc[thermal_var_new_rr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] = [0]* 168
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] = list(thermal_var_new_rr_down_on.loc[thermal_var_new_rr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] = [0]* 168

    #     ensemble_valeur_semaine[thermal_cluster]["nb_on"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])



    # for thermal_cluster in list_cluster_fr:
    #     de_accurate_base = pd.DataFrame(data = {
    #                                                 "energy_generation":ensemble_valeur_semaine[thermal_cluster]["energy_generation"],
    #                                                 "nodu":ensemble_valeur_semaine[thermal_cluster]["nb_on"],
    #                                                 "generation_reserve_up_primary_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"],
    #                                                 "generation_reserve_down_primary":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"],
    #                                                 "generation_reserve_up_secondary_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"],
    #                                                 "generation_reserve_down_secondary":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"],
    #                                                 "generation_reserve_up_tertiary1_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"],
    #                                                 "generation_reserve_down_tertiary1":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"],
    #                                                 "generation_reserve_up_tertiary1_off":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"],
    #                                                 "generation_reserve_up_tertiary2_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"],
    #                                                 # "generation_reserve_down_tertiary2":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"],
    #                                                 })
    #     de_accurate_base.to_csv("result_step2" + thermal_cluster.replace("*","_") + ".csv",index=False)



    cost2 = m.Objective().Value()

    temps_post_opti2 = time.perf_counter()

    cost = [cost1,cost2,cout_nodu]
    temps = [temps_post_read_mps-temps_initial,
             temps_conversion_fast-temps_post_read_mps,
             temps_load_bases-temps_conversion_fast,
             temps_post_opti1-temps_load_bases,
             temps_get_bases-temps_post_opti1,
             temps_lecture_resultat-temps_get_bases,
             temps_ensemble_valeur_semaine-temps_lecture_resultat,
             temps_heuristique_arrondi -temps_ensemble_valeur_semaine,
             temps_heuristique_dmin - temps_heuristique_arrondi,
             temps_changement_borne-temps_heuristique_dmin,
             temps_post_opti2 -temps_changement_borne,
             ]

    return (cost,temps,heure_defaillance,quantite_defaillance,bases)



def BP_week_fast_simple(output_path,ensemble_valeur_annuel,week,bases):

    temps_initial = time.perf_counter()

    m = read_mps(output_path,505,week,"XPRESS_LP")

    temps_post_read_mps = time.perf_counter()
    

    var = m.variables()
    contraintes = m.constraints()
    thermal_var_nodu = find_var(var,["NODU"])[0]
    list_thermal_clusters = thermal_var_nodu.cluster_name.unique()
    nbr_thermal_clusters = len(list_thermal_clusters)


    list_cluster_fr = []
    for thermal_cluster in list_thermal_clusters:
        nom_noeud= thermal_cluster.split("_",1)[0]
        if nom_noeud == "fr":
            list_cluster_fr.append(thermal_cluster)


    delete_constraint(contraintes, 168*3, 'POffUnitsLowerBound::area<fr>:')  #il y a 3 clusters avec de l'éteint
    
    delete_variable(var,m,168*nbr_thermal_clusters,'NumberStartingDispatchableUnits::area<')
    delete_variable(var,m,168*nbr_thermal_clusters,'NumberStoppingDispatchableUnits::area<')
    delete_variable(var,m,168*nbr_thermal_clusters,'NumberBreakingDownDispatchableUnits::area<')
    
    delete_constraint(contraintes,168*nbr_thermal_clusters,'NbDispUnitsMinBoundSinceMinUpTime::area<')
    delete_constraint(contraintes,168*nbr_thermal_clusters,'NbUnitsOutageLessThanNbUnitsStop::area<')
    delete_constraint(contraintes,168*nbr_thermal_clusters,'MinDownTime::area<')
    delete_constraint(contraintes,168*nbr_thermal_clusters,'ConsistenceNODU::area<')
    delete_constraint(contraintes,168*nbr_thermal_clusters,'PMaxDispatchableGeneration::area<')
    delete_constraint(contraintes,168*nbr_thermal_clusters,'PMinDispatchableGeneration::area<')



    list_cluster_fr_reserve = []
    nbr_reserve_x_cluster = 0
    nbr_cluster_avec_reserve = 0
    for thermal_cluster in list_cluster_fr:
        if len(ensemble_valeur_annuel[thermal_cluster]["reserve"]) != 0:
            list_cluster_fr_reserve.append(thermal_cluster)
            nbr_cluster_avec_reserve += 1
            nbr_reserve_x_cluster += len(ensemble_valeur_annuel[thermal_cluster]["reserve"])

    delete_constraint(contraintes,168*nbr_cluster_avec_reserve,'POutCapacityThreasholdInf::area<')
    delete_constraint(contraintes,168*nbr_cluster_avec_reserve,'POutCapacityThreasholdSup::area<')

    # delete_constraint(contraintes,168*nbr_reserve_x_cluster,'PMaxReserve::area<')

    var_id = [i for i in range(len(var)) if 'NODU::area<' in var[i].name()]
    assert len(var_id) in [0, 168*nbr_thermal_clusters]
    if len(var_id) == 168*nbr_thermal_clusters:
        for i in var_id:
            m.Objective().SetCoefficient(var[i], 0)


    temps_conversion_fast = time.perf_counter()


    # lp_format = m.ExportModelAsLpFormat(False)
    # with open("model_fast.lp","w") as file:
    #     file.write(lp_format)    

    if bases != None:
        load_basis(m,bases)

    temps_load_bases = time.perf_counter()

    solve_complete_problem(m)

    cost1 = m.Objective().Value()


    temps_post_opti1 = time.perf_counter()

    bases = get_basis(m)
    
    temps_get_bases = time.perf_counter()

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
    
    temps_lecture_resultat = time.perf_counter()

    list_thermal_clusters = thermal_var_production.cluster_name.unique()


    ensemble_valeur_semaine = {}

    for thermal_cluster in list_thermal_clusters:
        ensemble_valeur_semaine[thermal_cluster] = {}
        ensemble_valeur_semaine[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeur_semaine[thermal_cluster]["max_generating"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["ub"])
        ensemble_valeur_semaine[thermal_cluster]["min_generating"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["lb"])
        
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_fcr_up_on.loc[thermal_var_fcr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_fcr_down_on.loc[thermal_var_fcr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] = [0]* 168

        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] = list(thermal_var_afrr_up_on.loc[thermal_var_afrr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] = list(thermal_var_afrr_down_on.loc[thermal_var_afrr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] = [0]* 168

        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_mfrr_up_on.loc[thermal_var_mfrr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_mfrr_up_off.loc[thermal_var_mfrr_up_off["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] = list(thermal_var_mfrr_down_on.loc[thermal_var_mfrr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] = [0]* 168

        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] = list(thermal_var_new_rr_up_on.loc[thermal_var_new_rr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"] = list(thermal_var_new_rr_up_off.loc[thermal_var_new_rr_up_off["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"] = [0]* 168
        ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] = list(thermal_var_new_rr_down_on.loc[thermal_var_new_rr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] == []:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] = [0]* 168

        ensemble_valeur_semaine[thermal_cluster]["nb_on"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])

    # for thermal_cluster in list_cluster_fr:
    #     de_accurate_base = pd.DataFrame(data = {
    #                                             "energy_generation":ensemble_valeur_semaine[thermal_cluster]["energy_generation"],
    #                                             "nodu":ensemble_valeur_semaine[thermal_cluster]["nb_on"],
    #                                             "generation_reserve_up_primary_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"],
    #                                             "generation_reserve_down_primary":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"],
    #                                             "generation_reserve_up_secondary_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"],
    #                                             "generation_reserve_down_secondary":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"],
    #                                             "generation_reserve_up_tertiary1_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"],
    #                                             "generation_reserve_down_tertiary1":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"],
    #                                             "generation_reserve_up_tertiary1_off":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"],
    #                                             "generation_reserve_up_tertiary2_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"],
    #                                             "generation_reserve_down_tertiary2":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"],
    #                                             "generation_reserve_up_tertiary2_off":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"],
    #                                             })
    #     de_accurate_base.to_csv("result_step1_" + thermal_cluster.replace("*","_") + ".csv",index=False)

    temps_ensemble_valeur_semaine = time.perf_counter()

    nbr_guide = {}
    nbr_on_final = {}
    cout_nodu = 0


    for thermal_cluster in list_thermal_clusters:
        nbr_opti = [0] * 168
        for t in range(168):
            nbr_opti[t] = round(max(
                (ensemble_valeur_semaine[thermal_cluster]["energy_generation"][t] + ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"][t]+
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"][t]+ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"][t]+
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"][t]) / ensemble_valeur_annuel[thermal_cluster]["p_max"],
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_primary_reserve_up_on"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_primary_reserve_down"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_secondary_reserve_up_on"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_secondary_reserve_down"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_up_on"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_down"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_up_on"],0.0001)),
                 ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"][t]/(max(ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_down"],0.0001)),                                                                       
            ),7)
        nbr_guide[thermal_cluster] = [ceil(nbr_opti[t]) for t in range(168)]

    temps_heuristique_arrondi = time.perf_counter()

    for thermal_cluster in list_thermal_clusters:
        if ensemble_valeur_annuel[thermal_cluster]['dmin'] == 1 or nbr_guide[thermal_cluster].count(nbr_guide[thermal_cluster][0]) == 168:
            nbr_on = nbr_guide[thermal_cluster]
        else:
            nbr_on = heuristique_dmin_fast(ensemble_valeur_annuel[thermal_cluster]['dmin'],nbr_guide[thermal_cluster])

        nbr_max_dispo = np.ceil(np.round(np.array(ensemble_valeur_semaine[thermal_cluster]["max_generating"]) / ensemble_valeur_annuel[thermal_cluster]["p_max"],7))
        nbr_on_final[thermal_cluster] = [min(nbr_max_dispo[t],nbr_on[t]) for t in range(168)]

    temps_heuristique_dmin = time.perf_counter()

     
    id_contraintes_chgt_borne_inf = [ i for i in range(len(contraintes)) if 'POutBoundMin::area<' in contraintes[i].name()]
    id_contraintes_chgt_borne_sup = [ i for i in range(len(contraintes)) if 'POutBoundMax::area<' in contraintes[i].name()]


    for thermal_cluster in list_thermal_clusters:
        [nom_noeud,nom_cluster] = thermal_cluster.split("_",1)
        puissance_minimale = [ 0 ] * 168
        puissance_maximale = [ 0 ] * 168
        for t in range(168):
            puissance_min = min((nbr_on_final[thermal_cluster][t] * ensemble_valeur_annuel[thermal_cluster]["p_min"]),ensemble_valeur_semaine[thermal_cluster]["max_generating"][t])
            puissance_minimale[t] = (max(puissance_min,ensemble_valeur_semaine[thermal_cluster]["min_generating"][t],0))
            puissance_max = min((nbr_on_final[thermal_cluster][t] * ensemble_valeur_annuel[thermal_cluster]["p_max"]),ensemble_valeur_semaine[thermal_cluster]["max_generating"][t])
            puissance_maximale[t] = (max(puissance_max,ensemble_valeur_semaine[thermal_cluster]["min_generating"][t],0))
        
        cout_nodu += nbr_on_final[thermal_cluster][0] * ensemble_valeur_annuel[thermal_cluster]["fixed_cost"]
        for t in range(1,168):
            cout_nodu += nbr_on_final[thermal_cluster][t] * ensemble_valeur_annuel[thermal_cluster]["fixed_cost"]
            if nbr_on_final[thermal_cluster][t] > nbr_on_final[thermal_cluster][t-1]:
                cout_nodu += (nbr_on_final[thermal_cluster][t]-nbr_on_final[thermal_cluster][t-1]) * ensemble_valeur_annuel[thermal_cluster]["startup_cost"]

        nom_contrainte_cluster = '::ThermalCluster<' + nom_cluster + '>'
        cons_id_inf = [id_contraintes_chgt_borne_inf[i] for i in range(len(id_contraintes_chgt_borne_inf)) if nom_contrainte_cluster in contraintes[id_contraintes_chgt_borne_inf[i]].name()]
        cons_id_sup = [id_contraintes_chgt_borne_sup[i] for i in range(len(id_contraintes_chgt_borne_sup)) if nom_contrainte_cluster in contraintes[id_contraintes_chgt_borne_sup[i]].name()]
        
        id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
        for hour, id in enumerate(id_var):
            change_lower_bound(var,id,nbr_on_final[thermal_cluster][hour])
            change_upper_bound(var,id,nbr_on_final[thermal_cluster][hour])

        id_var = thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster,"id_var"]
        for hour, id in enumerate(id_var):
            if puissance_minimale[hour] != ensemble_valeur_semaine[thermal_cluster]["min_generating"][hour]:
                change_lower_bound(var,id,puissance_minimale[hour])
            if puissance_maximale[hour] != ensemble_valeur_semaine[thermal_cluster]["max_generating"][hour]:
                change_upper_bound(var,id,puissance_maximale[hour])
        
        for hour, id in enumerate(cons_id_inf):
            if puissance_minimale[hour] != ensemble_valeur_semaine[thermal_cluster]["min_generating"][hour]:
                contraintes[id].SetUb( - puissance_minimale[hour])
        for hour, id in enumerate(cons_id_sup):
            if puissance_maximale[hour] != ensemble_valeur_semaine[thermal_cluster]["max_generating"][hour]:
                contraintes[id].SetUb(puissance_maximale[hour])

    temps_changement_borne = time.perf_counter()

    # lp_format = m.ExportModelAsLpFormat(False)
    # with open("model_fast_2.lp","w") as file:
    #     file.write(lp_format)


    solve_complete_problem(m)
 


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

    # de_accurate_base = pd.DataFrame(nbr_guide)
    # de_accurate_base.to_csv("nbr_guide.csv",index=False)
     

    # de_accurate_base = pd.DataFrame(nbr_on_final)
    # de_accurate_base.to_csv("nbr_on_final.csv",index=False)


    # (thermal_var_production,thermal_var_nodu,thermal_var_reserves_on,thermal_var_reserves_off) = find_var(var,["DispatchableProduction","NODU","ParticipationOfRunningUnitsToReserve","ParticipationOfOffUnitsToReserve"])
    # thermal_var_fcr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_up"]
    # thermal_var_fcr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_down"]
    # thermal_var_afrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_up"]
    # thermal_var_afrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_down"]
    # thermal_var_mfrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_up"]
    # thermal_var_mfrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_down"]
    # thermal_var_mfrr_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="mfrr_up"]
    # thermal_var_new_rr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="new_rr_up"]
    # thermal_var_new_rr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="new_rr_down"]
    # thermal_var_new_rr_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="new_rr_up"]
    
    # temps_lecture_resultat = time.perf_counter()

    # list_thermal_clusters = thermal_var_production.cluster_name.unique()


    # ensemble_valeur_semaine = {}

    # for thermal_cluster in list_thermal_clusters:
    #     ensemble_valeur_semaine[thermal_cluster] = {}
    #     ensemble_valeur_semaine[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeur_semaine[thermal_cluster]["max_generating"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["ub"])
    #     ensemble_valeur_semaine[thermal_cluster]["min_generating"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["lb"])
        
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_fcr_up_on.loc[thermal_var_fcr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"] = [0]* 168
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_fcr_down_on.loc[thermal_var_fcr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"] = [0]* 168

    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] = list(thermal_var_afrr_up_on.loc[thermal_var_afrr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"] = [0]* 168
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] = list(thermal_var_afrr_down_on.loc[thermal_var_afrr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"] = [0]* 168

    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_mfrr_up_on.loc[thermal_var_mfrr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"] = [0]* 168
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_mfrr_up_off.loc[thermal_var_mfrr_up_off["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] = [0]* 168
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] = list(thermal_var_mfrr_down_on.loc[thermal_var_mfrr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"] = [0]* 168

    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] = list(thermal_var_new_rr_up_on.loc[thermal_var_new_rr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] = [0]* 168
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"] = list(thermal_var_new_rr_up_off.loc[thermal_var_new_rr_up_off["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"] = [0]* 168
    #     ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] = list(thermal_var_new_rr_down_on.loc[thermal_var_new_rr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     if ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] == []:
    #         ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] = [0]* 168

    #     ensemble_valeur_semaine[thermal_cluster]["nb_on"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])



    # for thermal_cluster in list_cluster_fr:
    #     de_accurate_base = pd.DataFrame(data = {"energy_generation":ensemble_valeur_semaine[thermal_cluster]["energy_generation"],
    #                                             "nodu":ensemble_valeur_semaine[thermal_cluster]["nb_on"],
    #                                             "generation_reserve_up_primary_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_primary_on"],
    #                                             "generation_reserve_down_primary":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_primary"],
    #                                             "generation_reserve_up_secondary_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_secondary_on"],
    #                                             "generation_reserve_down_secondary":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_secondary"],
    #                                             "generation_reserve_up_tertiary1_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_on"],
    #                                             "generation_reserve_down_tertiary1":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary1"],
    #                                             "generation_reserve_up_tertiary1_off":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"],
    #                                             "generation_reserve_up_tertiary2_on":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"],
    #                                             "generation_reserve_down_tertiary2":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"],
    #                                             "generation_reserve_up_tertiary2_off":ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"],
    #                                             })
    #     de_accurate_base.to_csv("result_step2" + thermal_cluster.replace("*","_") + ".csv",index=False)



    cost2 = m.Objective().Value()

    temps_post_opti2 = time.perf_counter()

    cost = [cost1,cost2,cout_nodu]
    temps = [temps_post_read_mps-temps_initial,
             temps_conversion_fast-temps_post_read_mps,
             temps_load_bases-temps_conversion_fast,
             temps_post_opti1-temps_load_bases,
             temps_get_bases-temps_post_opti1,
             temps_lecture_resultat-temps_get_bases,
             temps_ensemble_valeur_semaine-temps_lecture_resultat,
             temps_heuristique_arrondi -temps_ensemble_valeur_semaine,
             temps_heuristique_dmin - temps_heuristique_arrondi,
             temps_changement_borne-temps_heuristique_dmin,
             temps_post_opti2 -temps_changement_borne,
             ]

    return (cost,temps,heure_defaillance,quantite_defaillance,bases)