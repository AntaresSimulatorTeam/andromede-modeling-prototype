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
)
from andromede.thermal_heuristic.data import (
    get_max_failures,
    get_max_unit_for_min_down_time,
)
from andromede.simulation import (
    OutputValues,
)
from tests.bloc_BP_week.fonctions_week import *


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




def heuristique_dmin_accurate(dictionnaire_valeur,list_nbr_min):
    

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





def lecture_resultat_semaine(thermal_var_production,thermal_var_nodu,thermal_var_reserves_on,thermal_var_reserves_off,thermal_var_nodu_off,list_cluster,ensemble_valeur_annuel) -> dict[dict[list]]:

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

    ensemble_valeur_semaine = {}

    for thermal_cluster in list_cluster:
        ensemble_valeur_semaine[thermal_cluster] = {}
        ensemble_valeur_semaine[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeur_semaine[thermal_cluster]["nb_on"] = list(round(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"],6))
        ensemble_valeur_semaine[thermal_cluster]["nb_off_primary"] = [0] * 168
        ensemble_valeur_semaine[thermal_cluster]["nb_off_secondary"] = [0] * 168
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
            ensemble_valeur_semaine[thermal_cluster]["nb_off_tertiary1"] = list(thermal_var_nodu_off_mfrr.loc[thermal_var_nodu_off_mfrr["cluster_name"]==thermal_cluster]["sol"])
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_mfrr_up_off.loc[thermal_var_mfrr_up_off["cluster_name"]==thermal_cluster]["sol"])
        else:
            ensemble_valeur_semaine[thermal_cluster]["nb_off_tertiary1"] = [0] * 168

        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_up_on"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] = list(thermal_var_new_rr_up_on.loc[thermal_var_new_rr_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_down"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] = list(thermal_var_new_rr_down_on.loc[thermal_var_new_rr_down_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_up_off"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["nb_off_tertiary2"] = list(thermal_var_nodu_off_rr.loc[thermal_var_nodu_off_rr["cluster_name"]==thermal_cluster]["sol"])
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_off"] = list(thermal_var_new_rr_up_off.loc[thermal_var_new_rr_up_off["cluster_name"]==thermal_cluster]["sol"])
        else:
            ensemble_valeur_semaine[thermal_cluster]["nb_off_tertiary2"] = [0] * 168

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



def changement_contrainte_eteint(var,m):
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
            




def resolution_heuristique_arrondi(
        list_cluster,
        ensemble_valeur_annuel,
        ensemble_valeur_semaine,
        nbr_heuristique,
        heuristique,
        version: Optional[str]= None,
        option: Optional[str] = None,
        bonus: Optional[str] = None):
    
    for thermal_cluster in list_cluster:
        ensemble_valeurs = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]

        if version:
            if option:
                if bonus:
                    heuristique_resultat = heuristique([t for t in range(168)],ensemble_valeurs,version,option,bonus)
            else:
                heuristique_resultat = heuristique([t for t in range(168)],ensemble_valeurs,version)
        else:
            heuristique_resultat = heuristique([t for t in range(168)],ensemble_valeurs)

        nbr_heuristique[thermal_cluster] = []
        for t in range(168):
            nbr_heuristique[thermal_cluster].append(heuristique_resultat[t][0])

    return nbr_heuristique


def resolution_heuristique_arrondi_eteint(
        list_cluster,
        ensemble_valeur_annuel,
        ensemble_valeur_semaine,
        nbr_off_final,
        nbr_on_final,
        heuristique,
        option,
        bonus):
    
    for thermal_cluster in list_cluster:
        ensemble_valeurs = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]

        heuristique_resultat = heuristique([t for t in range(168)],ensemble_valeurs,nbr_on_final,option,bonus)

        nbr_off_final["fcr"][thermal_cluster] = [heuristique_resultat[t][0] for t in range(168)]
        nbr_off_final["afrr"][thermal_cluster] = [heuristique_resultat[t][1] for t in range(168)]
        nbr_off_final["mfrr"][thermal_cluster] = [heuristique_resultat[t][2] for t in range(168)]
        nbr_off_final["rr"][thermal_cluster] = [heuristique_resultat[t][3] for t in range(168)]

    return nbr_off_final



def resolution_heuristique_Dmin(list_cluster,ensemble_valeur_annuel,ensemble_valeur_semaine,nbr_heuristique,nbr_on_final):
    
    for thermal_cluster in list_cluster:
        ensemble_valeurs = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]
        if ((ensemble_valeurs["dmin_up"] == 1) and (ensemble_valeurs["dmin_down"] == 1)) or (nbr_heuristique[thermal_cluster] == list([nbr_heuristique[thermal_cluster][0]] * 168)):
            nbr_on_final[thermal_cluster] = nbr_heuristique[thermal_cluster]
        else:
            nbr_on_final[thermal_cluster] = heuristique_dmin_accurate(ensemble_valeurs,nbr_heuristique[thermal_cluster])

    return nbr_heuristique



def changement_bornes(list_cluster,thermal_var,var,dict_valeur):
    
    for thermal_cluster in list_cluster:
        id_var = thermal_var.loc[thermal_var["cluster_name"]==thermal_cluster,"id_var"]
        for hour, id in enumerate(id_var):
            change_lower_bound(var,id,ceil(dict_valeur[thermal_cluster][hour]))
            change_upper_bound(var,id,ceil(dict_valeur[thermal_cluster][hour]))

