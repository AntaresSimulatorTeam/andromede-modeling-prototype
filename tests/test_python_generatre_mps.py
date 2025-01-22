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




def test_generation_mps():

    study_path = "C:/Users/sonvicoleo/Documents/Test_finaux/Test_simple_noeud_double"
    antares_path = "D:/AppliRTE/bin/antares-solver.exe"
    # output_path = generate_mps_file(study_path,antares_path)
    # output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/Test_simple_noeud_unique/output/20250116-1104exp-export_mps"
    output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/Test_simple_noeud_double/output/20250122-1448exp-export_mps"

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


    thermal_var_production = find_thermal_var(m,"DispatchableProduction")
    thermal_var_nodu = find_thermal_var(m,"NODU")
    thermal_var_reserves_on = find_thermal_var(m,"ParticipationOfRunningUnitsToReserve")
    thermal_var_primary_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="primary_up"]
    thermal_var_primary_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="primary_down"]
    thermal_var_tertiary_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary_up"]
    thermal_var_tertiary_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary_down"]
    thermal_var_reserves_off = find_thermal_var(m,"ParticipationOfOffUnitsToReserve")
    thermal_var_tertiary_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="tertiary_up"]
    
    thermal_areas = get_ini_file(study_path + "/input/thermal/areas.ini")
    

    list_areas_thermique = thermal_var_nodu.name_antares_object.unique()
    thermal_list = {}
    reserves_areas_cost = {}

    reserve_cluster = {}
    reserve_cluster["primary_up"] = {}
    reserve_cluster["primary_down"] = {}
    reserve_cluster["tertiary_up"] = {}
    reserve_cluster["tertiary_down"] = {}

    for area in list_areas_thermique:
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

    
    ensemble_valeurs = {}

    for thermal_cluster in list_thermal_clusters:
        ensemble_valeurs[thermal_cluster] = {}
        ensemble_valeurs[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["nb_on"] = list(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])

        [nom_noeud,nom_cluster] = thermal_cluster.split("_")
        ensemble_valeurs[thermal_cluster]["p_max"] =  [ thermal_list[nom_noeud].getfloat(nom_cluster,"nominalcapacity") for t in range(168)]
        if thermal_list[nom_noeud].has_option(nom_cluster,"p_min"):
            ensemble_valeurs[thermal_cluster]["p_min"] =  [ thermal_list[nom_noeud].getfloat(nom_cluster,"min-stable-power") for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["p_min"] = [ 0 for t in range(168)]
        if thermal_list[nom_noeud].has_option(nom_cluster,"min-up-time"):
            ensemble_valeurs[thermal_cluster]["dmin_up"] = thermal_list[nom_noeud].getint(nom_cluster,"min-up-time")
        else:
            ensemble_valeurs[thermal_cluster]["dmin_up"] = 1
        if thermal_list[nom_noeud].has_option(nom_cluster,"min-down-time"):
            ensemble_valeurs[thermal_cluster]["dmin_down"] = thermal_list[nom_noeud].getint(nom_cluster,"min-down-time")
        else:
            ensemble_valeurs[thermal_cluster]["dmin_down"] = 1
        if thermal_list[nom_noeud].has_option(nom_cluster,"cost"):
            ensemble_valeurs[thermal_cluster]["cost"] =  [ thermal_list[nom_noeud].getfloat(nom_cluster,"marginal-cost") for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["cost"] = [ 0 for t in range(168)]
        if thermal_list[nom_noeud].has_option(nom_cluster,"startup_cost"):
            ensemble_valeurs[thermal_cluster]["startup_cost"] =  [ thermal_list[nom_noeud].getfloat(nom_cluster,"startup-cost") for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["startup_cost"] = [ 0 for t in range(168)]
        if thermal_list[nom_noeud].has_option(nom_cluster,"fixed-cost"):
            ensemble_valeurs[thermal_cluster]["fixed_cost"] =  [ thermal_list[nom_noeud].getfloat(nom_cluster,"fixed-cost") for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["fixed_cost"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["ens_cost"] =  [ thermal_areas.getfloat('unserverdenergycost',nom_noeud) for t in range(168)]

        if reserves_areas_cost[nom_noeud].has_option('primary_up','failure-cost'):
            ensemble_valeurs[thermal_cluster]["primary_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('primary_up','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["primary_reserve_up_not_supplied_cost"] = [ 0 for t in range(168)]
        if reserves_areas_cost[nom_noeud].has_option('primary_up','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["primary_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('primary_up','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["primary_reserve_up_oversupplied_cost"] = [ 0 for t in range(168)]
        if reserves_areas_cost[nom_noeud].has_option('primary_down','failure-cost'):
            ensemble_valeurs[thermal_cluster]["primary_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('primary_down','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["primary_reserve_down_not_supplied_cost"] = [ 0 for t in range(168)]
        if reserves_areas_cost[nom_noeud].has_option('primary_down','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["primary_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('primary_down','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["primary_reserve_down_oversupplied_cost"] = [ 0 for t in range(168)]
        if reserves_areas_cost[nom_noeud].has_option('tertiary_up','failure-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('tertiary_up','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_not_supplied_cost"] = [ 0 for t in range(168)]
        if reserves_areas_cost[nom_noeud].has_option('tertiary_up','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('tertiary_up','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_oversupplied_cost"] = [ 0 for t in range(168)]
        if reserves_areas_cost[nom_noeud].has_option('tertiary_down','failure-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('tertiary_down','failure-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_not_supplied_cost"] = [ 0 for t in range(168)]
        if reserves_areas_cost[nom_noeud].has_option('tertiary_down','spillage-cost'):
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost[nom_noeud].getfloat('tertiary_down','spillage-cost') for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_oversupplied_cost"] = [ 0 for t in range(168)]
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

        ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_on"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary2"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_off"] =  [ 0 for t in range(168)]
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_tertiary_up_off.loc[thermal_var_tertiary_up_off["cluster_name"]==thermal_cluster]["sol"])
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_off"] =  [ 0 for t in range(168)]


        if (nom_cluster in reserve_cluster["primary_up"]) and ('max-power' in reserve_cluster["primary_up"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_on"] = [ reserve_cluster["primary_up"][nom_cluster]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_primary_up_on.loc[thermal_var_primary_up_on["cluster_name"]==thermal_cluster]["sol"])
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_on"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"] = [ 0 for t in range(168)]
        
        if (nom_cluster in reserve_cluster["primary_down"]) and ('max-power' in reserve_cluster["primary_down"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_down"] = [ reserve_cluster["primary_down"][nom_cluster]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_primary_down_on.loc[thermal_var_primary_down_on["cluster_name"]==thermal_cluster]["sol"])
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_down"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"] = [ 0 for t in range(168)]

        if (nom_cluster in reserve_cluster["tertiary_up"]) and ('max-power' in reserve_cluster["tertiary_up"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_on"] = [ reserve_cluster["tertiary_up"][nom_cluster]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_tertiary_up_on.loc[thermal_var_tertiary_up_on["cluster_name"]==thermal_cluster]["sol"])
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_on"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"] = [ 0 for t in range(168)]
        
        if (nom_cluster in reserve_cluster["tertiary_down"]) and ('max-power' in reserve_cluster["tertiary_down"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_down"] = [ reserve_cluster["tertiary_down"][nom_cluster]['max-power'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"] = list(thermal_var_tertiary_down_on.loc[thermal_var_tertiary_down_on["cluster_name"]==thermal_cluster]["sol"])
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_down"] = [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"] = [ 0 for t in range(168)]
        
        if (nom_cluster in reserve_cluster["tertiary_up"]) and ('max-power-off' in reserve_cluster["tertiary_up"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_off"] =  [ reserve_cluster["tertiary_up"][nom_cluster]['max-power-off'] for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_tertiary_up_off.loc[thermal_var_tertiary_up_off["cluster_name"]==thermal_cluster]["sol"])
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary1_reserve_up_off"] =  [ 0 for t in range(168)]
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"] = [ 0 for t in range(168)]



        if (nom_cluster in reserve_cluster["primary_up"]) and ('max-power' in reserve_cluster["primary_up"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_up_on"] =  [ reserve_cluster["primary_up"][nom_cluster]['max-power'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_up_on"] =  [ 0 for t in range(168)]
        if (nom_cluster in reserve_cluster["primary_down"]) and ('participation-cost' in reserve_cluster["primary_down"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_down"] =  [ reserve_cluster["primary_down"][nom_cluster]['participation-cost'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_down"] =  [ 0 for t in range(168)]
        if (nom_cluster in reserve_cluster["tertiary_up"]) and ('participation-cost' in reserve_cluster["tertiary_up"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_on"] =  [ reserve_cluster["tertiary_up"][nom_cluster]['participation-cost'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_on"] =  [ 0 for t in range(168)]
        if (nom_cluster in reserve_cluster["tertiary_down"]) and ('participation-cost' in reserve_cluster["tertiary_down"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_down"] =  [ reserve_cluster["tertiary_down"][nom_cluster]['participation-cost'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_down"] =  [ 0 for t in range(168)]
        if (nom_cluster in reserve_cluster["tertiary_up"]) and ('participation-cost-off' in reserve_cluster["tertiary_up"][nom_cluster]):
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_off"] =  [ reserve_cluster["tertiary_up"][nom_cluster]['participation-cost-off'] for t in range(168)]
        else:
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary1_reserve_up_off"] =  [ 0 for t in range(168)]
        
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
        ensemble_valeurs[thermal_cluster]["min_generating"] =  [ 0 for t in range(168)]

        disponibilite_puissance = np.loadtxt(study_path +  "/input/thermal/series/"+ nom_noeud +"/" + nom_cluster + "/series.txt")[0:168]
        disponibilite = np.ceil(disponibilite_puissance / ensemble_valeurs[thermal_cluster]["p_max"])
        ensemble_valeurs[thermal_cluster]["nb_units_max_invisible"] = disponibilite
        ensemble_valeurs[thermal_cluster]["nb_units_max"] = disponibilite
        ensemble_valeurs[thermal_cluster]["max_generating"] = disponibilite_puissance




    nbr_on_accurate_step1_base = ensemble_valeurs['area_base']['nb_on']
    # nbr_off_primary_accurate_step1_base = ensemble_valeurs['area_base']['nb_off_primary']
    energy_production_accurate_step1_base = ensemble_valeurs['area_base']['energy_generation']
    reserve_primary_up_on_production_accurate_step1_base = ensemble_valeurs['area_base']['generation_reserve_up_primary_on']
    reserve_primary_up_off_production_accurate_step1_base = ensemble_valeurs['area_base']['generation_reserve_up_primary_off']   
    reserve_primary_down_production_accurate_step1_base = ensemble_valeurs['area_base']['generation_reserve_down_primary']   
    # nbr_off_secondary_accurate_step1_base = ensemble_valeurs['area_base']['nb_off_secondary']
    reserve_secondary_up_on_production_accurate_step1_base = ensemble_valeurs['area_base']['generation_reserve_up_secondary_on']
    reserve_secondary_up_off_production_accurate_step1_base = ensemble_valeurs['area_base']['generation_reserve_up_secondary_off']
    reserve_secondary_down_production_accurate_step1_base = ensemble_valeurs['area_base']['generation_reserve_down_secondary']   
    # nbr_off_tertiary1_accurate_step1_base = ensemble_valeurs['area_base']['nb_off_tertiary1']
    reserve_tertiary1_up_on_production_accurate_step1_base = ensemble_valeurs['area_base']['generation_reserve_up_tertiary1_on']
    reserve_tertiary1_up_off_production_accurate_step1_base = ensemble_valeurs['area_base']['generation_reserve_up_tertiary1_off']
    reserve_tertiary1_down_production_accurate_step1_base = ensemble_valeurs['area_base']['generation_reserve_down_tertiary1']   
   

    de_accurate_step1_base = pd.DataFrame(data = {"energy_production_base": energy_production_accurate_step1_base,"nbr_on": nbr_on_accurate_step1_base,
                                            #  "nbr_off_primary_base": nbr_off_primary_accurate_step1_base[0],
                                             "reserve_primary_up_on_base":reserve_primary_up_on_production_accurate_step1_base,
                                            #  "reserve_primary_up_off_base":reserve_primary_up_off_production_accurate_step1_base[0],
                                             "reserve_primary_down_base":reserve_primary_down_production_accurate_step1_base,
                                            #  "nbr_off_secondary_base": nbr_off_secondary_accurate_step1_base[0],
                                            #  "reserve_secondary_up_on_base":reserve_secondary_up_on_production_accurate_step1_base[0],"reserve_secondary_up_off_base":reserve_secondary_up_off_production_accurate_step1_base[0], "reserve_secondary_down_base":reserve_secondary_down_production_accurate_step1_base[0],
                                            #  "nbr_off_tertiary1_base": nbr_off_tertiary1_accurate_step1_base[0],
                                             "reserve_tertiary1_up_on_base":reserve_tertiary1_up_on_production_accurate_step1_base,"reserve_tertiary1_up_off_base":reserve_tertiary1_up_off_production_accurate_step1_base, "reserve_tertiary1_down_base":reserve_tertiary1_down_production_accurate_step1_base,
                                             "Fonction_objectif":cost})
    de_accurate_step1_base.to_csv("result_mps_step1_base.csv",index=False)

    nbr_on_accurate_step1_peak = ensemble_valeurs['area_peak']['nb_on']
    # nbr_off_primary_accurate_step1_peak = ensemble_valeurs['area_peak']['nb_off_primary']
    energy_production_accurate_step1_peak = ensemble_valeurs['area_peak']['energy_generation']
    reserve_primary_up_on_production_accurate_step1_peak = ensemble_valeurs['area_peak']['generation_reserve_up_primary_on']
    reserve_primary_up_off_production_accurate_step1_peak = ensemble_valeurs['area_peak']['generation_reserve_up_primary_off']   
    reserve_primary_down_production_accurate_step1_peak = ensemble_valeurs['area_peak']['generation_reserve_down_primary']   
    # nbr_off_secondary_accurate_step1_peak = ensemble_valeurs['area_peak']['nb_off_secondary']
    reserve_secondary_up_on_production_accurate_step1_peak = ensemble_valeurs['area_peak']['generation_reserve_up_secondary_on']
    reserve_secondary_up_off_production_accurate_step1_peak = ensemble_valeurs['area_peak']['generation_reserve_up_secondary_off']
    reserve_secondary_down_production_accurate_step1_peak = ensemble_valeurs['area_peak']['generation_reserve_down_secondary']   
    # nbr_off_tertiary1_accurate_step1_peak = ensemble_valeurs['area_peak']['nb_off_tertiary1']
    reserve_tertiary1_up_on_production_accurate_step1_peak = ensemble_valeurs['area_peak']['generation_reserve_up_tertiary1_on']
    reserve_tertiary1_up_off_production_accurate_step1_peak = ensemble_valeurs['area_peak']['generation_reserve_up_tertiary1_off']
    reserve_tertiary1_down_production_accurate_step1_peak = ensemble_valeurs['area_peak']['generation_reserve_down_tertiary1']   
   

    de_accurate_step1_peak = pd.DataFrame(data = {"energy_production_peak": energy_production_accurate_step1_peak,"nbr_on": nbr_on_accurate_step1_peak,
                                            #  "nbr_off_primary_peak": nbr_off_primary_accurate_step1_peak[0],
                                             "reserve_primary_up_on_peak":reserve_primary_up_on_production_accurate_step1_peak,
                                            #  "reserve_primary_up_off_peak":reserve_primary_up_off_production_accurate_step1_peak[0],
                                             "reserve_primary_down_peak":reserve_primary_down_production_accurate_step1_peak,
                                            #  "nbr_off_secondary_peak": nbr_off_secondary_accurate_step1_peak[0],
                                            #  "reserve_secondary_up_on_peak":reserve_secondary_up_on_production_accurate_step1_peak[0],"reserve_secondary_up_off_peak":reserve_secondary_up_off_production_accurate_step1_peak[0], "reserve_secondary_down_peak":reserve_secondary_down_production_accurate_step1_peak[0],
                                            #  "nbr_off_tertiary1_peak": nbr_off_tertiary1_accurate_step1_peak[0],
                                             "reserve_tertiary1_up_on_peak":reserve_tertiary1_up_on_production_accurate_step1_peak,"reserve_tertiary1_up_off_peak":reserve_tertiary1_up_off_production_accurate_step1_peak, "reserve_tertiary1_down_peak":reserve_tertiary1_down_production_accurate_step1_peak
                                             })
    de_accurate_step1_peak.to_csv("result_mps_step1_peak.csv",index=False)








    heuristique_resultat = {}
    nbr_on_final = {}

    for thermal_cluster in list_thermal_clusters:
        heuristique_resultat[thermal_cluster] = heuristique_opti_repartition_sans_pmin(
            [t for t in range(168)],
            ensemble_valeurs[thermal_cluster],
            "choix",    # version
            # "choix", # option
            # "réduction", # bonus
            )


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

        # thermal_problem_builder.update_database_heuristic(
        #     OutputValues(resolution_step_accurate_heuristic),
        #     week_scenario_index,
        #     [g],
        #     param_to_update= [["nb_units_min","nb_units_max"]],
        #     var_to_read=["nb_on"],
        #     fn_to_apply= old_heuristique,
        # )

        nbr_on_final[thermal_cluster] = OutputValues(resolution_step_accurate_heuristic)._components[thermal_cluster]._variables['nb_on'].value[0]

        id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
        for hour, id in enumerate(id_var):
            # variable = all_vars[thermal_var_nodu["id_var"]==id_var]
            change_lower_bound(m,id,ceil(nbr_on_final[thermal_cluster][hour]))
            change_upper_bound(m,id,ceil(nbr_on_final[thermal_cluster][hour]))
    





    lp_format = m.ExportModelAsLpFormat(False)
    with open("model_2.lp","w") as file:
        file.write(lp_format)


    solve_complete_problem(m)
    cost = m.Objective().Value()



    thermal_var_production = find_thermal_var(m,"DispatchableProduction")
    thermal_var_nodu = find_thermal_var(m,"NODU")
    thermal_var_reserves_on = find_thermal_var(m,"ParticipationOfRunningUnitsToReserve")
    thermal_var_primary_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="primary_up"]
    thermal_var_primary_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="primary_down"]
    thermal_var_tertiary_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary_up"]
    thermal_var_tertiary_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary_down"]
    thermal_var_reserves_off = find_thermal_var(m,"ParticipationOfOffUnitsToReserve")
    thermal_var_tertiary_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="tertiary_up"]
    


    nbr_final_base = nbr_on_final["area_base"]
    nbr_on_accurate_step2_base = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]=="area_base"]["sol"])
    # nbr_off_primary_accurate_step2_base = ensemble_valeurs['area_base']['nb_off_primary']
    energy_production_accurate_step2_base = list(thermal_var_production.loc[thermal_var_production["cluster_name"]=="area_base"]["sol"])
    reserve_primary_up_on_production_accurate_step2_base = list(thermal_var_primary_up_on.loc[thermal_var_primary_up_on["cluster_name"]=="area_base"]["sol"])
    # reserve_primary_up_off_production_accurate_step2_base = ensemble_valeurs['area_base']['generation_reserve_up_primary_off']   
    reserve_primary_down_production_accurate_step2_base = list(thermal_var_primary_down_on.loc[thermal_var_primary_down_on["cluster_name"]=="area_base"]["sol"])
    # nbr_off_secondary_accurate_step2_base = ensemble_valeurs['area_base']['nb_off_secondary']
    # reserve_secondary_up_on_production_accurate_step2_base = ensemble_valeurs['area_base']['generation_reserve_up_secondary_on']
    # reserve_secondary_up_off_production_accurate_step2_base = ensemble_valeurs['area_base']['generation_reserve_up_secondary_off']
    # reserve_secondary_down_production_accurate_step2_base = ensemble_valeurs['area_base']['generation_reserve_down_secondary']   
    # nbr_off_tertiary2_accurate_step2_base = ensemble_valeurs['area_base']['nb_off_tertiary2']
    reserve_tertiary2_up_on_production_accurate_step2_base = list(thermal_var_tertiary_up_on.loc[thermal_var_tertiary_up_on["cluster_name"]=="area_base"]["sol"])
    reserve_tertiary2_up_off_production_accurate_step2_base = list(thermal_var_tertiary_up_off.loc[thermal_var_tertiary_up_off["cluster_name"]=="area_base"]["sol"])
    reserve_tertiary2_down_production_accurate_step2_base = list(thermal_var_tertiary_down_on.loc[thermal_var_tertiary_down_on["cluster_name"]=="area_base"]["sol"])
   

    de_accurate_step2_base = pd.DataFrame(data = {
                                            # "nbr_on_final": nbr_final_base,
                                            "energy_production_base": energy_production_accurate_step2_base,"nbr_on": nbr_on_accurate_step2_base,
                                            #  "nbr_off_primary_base": nbr_off_primary_accurate_step2_base[0],
                                             "reserve_primary_up_on_base":reserve_primary_up_on_production_accurate_step2_base,
                                            #  "reserve_primary_up_off_base":reserve_primary_up_off_production_accurate_step2_base[0],
                                             "reserve_primary_down_base":reserve_primary_down_production_accurate_step2_base,
                                            #  "nbr_off_secondary_base": nbr_off_secondary_accurate_step2_base[0],
                                            #  "reserve_secondary_up_on_base":reserve_secondary_up_on_production_accurate_step2_base[0],"reserve_secondary_up_off_base":reserve_secondary_up_off_production_accurate_step2_base[0], "reserve_secondary_down_base":reserve_secondary_down_production_accurate_step2_base[0],
                                            #  "nbr_off_tertiary2_base": nbr_off_tertiary2_accurate_step2_base[0],
                                             "reserve_tertiary2_up_on_base":reserve_tertiary2_up_on_production_accurate_step2_base,"reserve_tertiary2_up_off_base":reserve_tertiary2_up_off_production_accurate_step2_base, "reserve_tertiary2_down_base":reserve_tertiary2_down_production_accurate_step2_base,
                                             "Fonction_objectif":cost
                                            })
    de_accurate_step2_base.to_csv("result_mps_step2_base.csv",index=False)



    nbr_final_peak = nbr_on_final["area_peak"]
    nbr_on_accurate_step2_peak = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]=="area_peak"]["sol"])
    # nbr_off_primary_accurate_step2_peak = ensemble_valeurs['area_peak']['nb_off_primary']
    energy_production_accurate_step2_peak = list(thermal_var_production.loc[thermal_var_production["cluster_name"]=="area_peak"]["sol"])
    reserve_primary_up_on_production_accurate_step2_peak = list(thermal_var_primary_up_on.loc[thermal_var_primary_up_on["cluster_name"]=="area_peak"]["sol"])
    # reserve_primary_up_off_production_accurate_step2_peak = ensemble_valeurs['area_peak']['generation_reserve_up_primary_off']   
    reserve_primary_down_production_accurate_step2_peak = list(thermal_var_primary_down_on.loc[thermal_var_primary_down_on["cluster_name"]=="area_peak"]["sol"]) 
    # nbr_off_secondary_accurate_step2_peak = ensemble_valeurs['area_peak']['nb_off_secondary']
    # reserve_secondary_up_on_production_accurate_step2_peak = ensemble_valeurs['area_peak']['generation_reserve_up_secondary_on']
    # reserve_secondary_up_off_production_accurate_step2_peak = ensemble_valeurs['area_peak']['generation_reserve_up_secondary_off']
    # reserve_secondary_down_production_accurate_step2_peak = ensemble_valeurs['area_peak']['generation_reserve_down_secondary']   
    # nbr_off_tertiary2_accurate_step2_peak = ensemble_valeurs['area_peak']['nb_off_tertiary2']
    reserve_tertiary2_up_on_production_accurate_step2_peak = list(thermal_var_tertiary_up_on.loc[thermal_var_tertiary_up_on["cluster_name"]=="area_peak"]["sol"])
    reserve_tertiary2_up_off_production_accurate_step2_peak = list(thermal_var_tertiary_up_off.loc[thermal_var_tertiary_up_off["cluster_name"]=="area_peak"]["sol"])
    reserve_tertiary2_down_production_accurate_step2_peak = list(thermal_var_tertiary_down_on.loc[thermal_var_tertiary_down_on["cluster_name"]=="area_peak"]["sol"])

    de_accurate_step2_peak = pd.DataFrame(data = {
                                            # "nbr_on_final": nbr_final_peak,
                                            "energy_production_peak": energy_production_accurate_step2_peak,"nbr_on": nbr_on_accurate_step2_peak,
                                            #  "nbr_off_primary_peak": nbr_off_primary_accurate_step2_peak[0],
                                             "reserve_primary_up_on_peak":reserve_primary_up_on_production_accurate_step2_peak,
                                            #  "reserve_primary_up_off_peak":reserve_primary_up_off_production_accurate_step2_peak[0],
                                             "reserve_primary_down_peak":reserve_primary_down_production_accurate_step2_peak,
                                            #  "nbr_off_secondary_peak": nbr_off_secondary_accurate_step2_peak[0],
                                            #  "reserve_secondary_up_on_peak":reserve_secondary_up_on_production_accurate_step2_peak[0],"reserve_secondary_up_off_peak":reserve_secondary_up_off_production_accurate_step2_peak[0], "reserve_secondary_down_peak":reserve_secondary_down_production_accurate_step2_peak[0],
                                            #  "nbr_off_tertiary2_peak": nbr_off_tertiary2_accurate_step2_peak[0],
                                             "reserve_tertiary2_up_on_peak":reserve_tertiary2_up_on_production_accurate_step2_peak,"reserve_tertiary2_up_off_peak":reserve_tertiary2_up_off_production_accurate_step2_peak, "reserve_tertiary2_down_peak":reserve_tertiary2_down_production_accurate_step2_peak
                                             })
    de_accurate_step2_peak.to_csv("result_mps_step2_peak.csv",index=False)












    # get_max_unit_for_min_down_time in src/andromede/thermal_heuristic/cluster_paramterer.py/compute_cluster_paramterer