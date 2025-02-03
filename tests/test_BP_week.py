from tests.generate_mps_files import *
from math import ceil,floor
import numpy as np
import time
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



def test_BP_first_week():
    study_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_france_year"    
    output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_france_year/output/20250131-0943exp-export_mps"


    (ensemble_valeur_annuel,ensemble_dmins_etranger) = lecture_donnees(study_path)

    return BP_week(study_path,output_path,ensemble_valeur_annuel,ensemble_dmins_etranger,20)


def test_heuristique_dmin():
    dictionnaire_valeur = {}
    dictionnaire_valeur["dmin_up"] = 1
    dictionnaire_valeur["dmin_down"] = 1
    dictionnaire_valeur["nb_units_max"] = [2] * 24 + [3] * 144
    list_nbr_min = [0] * 168
    list_nbr_min[113] = 3
    list_nbr_min[114] = 3
    list_nbr_min[115] = 3
    list_nbr_min[116] = 3
    list_nbr_min[126] = 3
    list_nbr_min[127] = 3
    list_nbr_min[128] = 3
    list_nbr_min[129] = 3
    list_nbr_min[137] = 3
    list_nbr_min[138] = 3
    list_nbr_min[139] = 3
    list_nbr_min[140] = 3
    list_nbr_min[141] = 3
    list_nbr_min[142] = 3
    list_nbr_min[143] = 3
    list_nbr_min[150] = 3
    list_nbr_min[151] = 3
    list_nbr_min[152] = 3
    list_nbr_min[153] = 3
    list_nbr_min[160] = 3
    list_nbr_min[161] = 3
    list_nbr_min[162] = 3
    list_nbr_min[163] = 3
    list_nbr_min[164] = 2
    list_nbr_min[165] = 2
    list_nbr_min[166] = 2
    list_nbr_min[167] = 2

    result = heuristique_dmin(dictionnaire_valeur,list_nbr_min)
    return result




def lecture_donnees(study_path):

    

    thermal_areas = get_ini_file(study_path + "/input/thermal/areas.ini")
    list_area = thermal_areas.options('unserverdenergycost')

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
                ensemble_dmins_etranger[thermal_cluster][dmin_up] = dmin_up
                ensemble_dmins_etranger[thermal_cluster][dmin_down] = dmin_down


    ens_cost = thermal_areas.getfloat('unserverdenergycost',"fr")
    reserve_cluster = {}
    reserve_cluster["fcr_up"] = {}
    reserve_cluster["fcr_down"] = {}
    reserve_cluster["afrr_up"] = {}
    reserve_cluster["afrr_down"] = {}
    reserve_cluster["mfrr_up"] = {}
    reserve_cluster["mfrr_down"] = {}
    reserve_cluster["tertiary2_up"] = {}
    reserve_cluster["tertiary2_down"] = {}


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
    reserves_areas_cost["fcr_up"]['failure-cost'] = file_cost.getfloat('fcr_up','failure-cost')
    reserves_areas_cost["fcr_up"]['spillage-cost'] = file_cost.getfloat('fcr_up','spillage-cost')
    reserves_areas_cost["fcr_down"] = {}
    reserves_areas_cost["fcr_down"]['failure-cost'] = file_cost.getfloat('fcr_down','failure-cost')
    reserves_areas_cost["fcr_down"]['spillage-cost'] = file_cost.getfloat('fcr_down','spillage-cost')
    reserves_areas_cost["afrr_up"] = {}
    reserves_areas_cost["afrr_up"]['failure-cost'] = file_cost.getfloat('afrr_up','failure-cost')
    reserves_areas_cost["afrr_up"]['spillage-cost'] = file_cost.getfloat('afrr_up','spillage-cost')
    reserves_areas_cost["afrr_down"] = {}
    reserves_areas_cost["afrr_down"]['failure-cost'] = file_cost.getfloat('afrr_down','failure-cost')
    reserves_areas_cost["afrr_down"]['spillage-cost'] = file_cost.getfloat('afrr_down','spillage-cost')
    reserves_areas_cost["mfrr_up"] = {}
    reserves_areas_cost["mfrr_up"]['failure-cost'] = file_cost.getfloat('mfrr_up','failure-cost')
    reserves_areas_cost["mfrr_up"]['spillage-cost'] = file_cost.getfloat('mfrr_up','spillage-cost')
    reserves_areas_cost["mfrr_down"] = {}
    reserves_areas_cost["mfrr_down"]['failure-cost'] = file_cost.getfloat('mfrr_down','failure-cost')
    reserves_areas_cost["mfrr_down"]['spillage-cost'] = file_cost.getfloat('mfrr_down','spillage-cost')
    reserves_areas_cost["tertiary2_up"] = {}
    reserves_areas_cost["tertiary2_up"]['failure-cost'] = 0
    reserves_areas_cost["tertiary2_up"]['spillage-cost'] = 0
    reserves_areas_cost["tertiary2_down"] = {}
    reserves_areas_cost["tertiary2_down"]['failure-cost'] = 0
    reserves_areas_cost["tertiary2_down"]['spillage-cost'] = 0

    
    
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
        ensemble_valeurs[thermal_cluster]["secondary_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost["afrr_up"]['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["secondary_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost['afrr_down']['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["secondary_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost['afrr_down']['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost["mfrr_up"]['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost["mfrr_up"]['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost['mfrr_down']['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary1_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost['mfrr_down']['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_up_not_supplied_cost"] =  [ reserves_areas_cost["tertiary2_up"]['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_up_oversupplied_cost"] =  [ reserves_areas_cost["tertiary2_up"]['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_down_not_supplied_cost"] =  [ reserves_areas_cost['tertiary2_down']['failure-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["tertiary2_reserve_down_oversupplied_cost"] =  [ reserves_areas_cost['tertiary2_down']['spillage-cost'] ] * 168
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["participation_max_primary_reserve_up_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["participation_max_secondary_reserve_up_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["cost_participation_primary_reserve_up_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["cost_participation_secondary_reserve_up_off"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_off"] =  [ 0 ] * 168


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


  


        if (nom_cluster in reserve_cluster["tertiary2_up"]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_on"] = [ reserve_cluster["tertiary2_up"][nom_cluster]['max-power'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_on"] =  [ reserve_cluster["tertiary2_up"][nom_cluster]['participation-cost'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_up_on"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary2_on"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_up_on"] =  [ 0 ] * 168
        if (nom_cluster in reserve_cluster["tertiary2_down"]):
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_down"] = [ reserve_cluster["tertiary2_down"][nom_cluster]['max-power'] ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_down"] =  [ reserve_cluster["tertiary2_down"][nom_cluster]['participation-cost'] ] * 168
        else:
            ensemble_valeurs[thermal_cluster]["participation_max_tertiary2_reserve_down"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary2"] = [ 0 ] * 168
            ensemble_valeurs[thermal_cluster]["cost_participation_tertiary2_reserve_down"] =  [ 0 ] * 168
      
         
        ensemble_valeurs[thermal_cluster]["spillage_cost"] =  [ 0 ] * 168
        ensemble_valeurs[thermal_cluster]["min_generating"] =  [ 0 ] * 168
        




    return(ensemble_valeurs,ensemble_dmins_etranger)


def heuristique_dmin(dictionnaire_valeur,list_nbr_min):
        
        
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
        resolution_step_accurate_heuristic.solver.EnableOutput()
        status = resolution_step_accurate_heuristic.solver.Solve()
        assert status == pywraplp.Solver.OPTIMAL

        return(OutputValues(resolution_step_accurate_heuristic)._components[thermal_cluster]._variables['nb_on'].value[0])



def BP_week(study_path,output_path,ensemble_valeur_annuel,ensemble_dmins_etranger,week):

    

    m = read_mps(output_path,1,week,"XPRESS")
    
    contraintes = m.constraints()

    delete_constraint(contraintes, 168*4, 'POffUnitsLowerBound::area<fr>:')

    var = m.variables()

    # lp_format = m.ExportModelAsLpFormat(False)
    # with open("model.lp","w") as file:
    #     file.write(lp_format)


    solve_complete_problem(m)
    # basis = get_basis(m)
    a = m.Iterations()
 

    cost1 = m.Objective().Value()


    thermal_var_production = find_thermal_var(var,"DispatchableProduction")
    thermal_var_nodu = find_thermal_var(var,"NODU")

    thermal_var_reserves_on = find_thermal_var(var,"ParticipationOfRunningUnitsToReserve")
    thermal_var_fcr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_up"]
    thermal_var_fcr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_down"]
    thermal_var_afrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_up"]
    thermal_var_afrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_down"]
    thermal_var_mfrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_up"]
    thermal_var_mfrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_down"]
    thermal_var_reserves_off = find_thermal_var(var,"ParticipationOfOffUnitsToReserve")
    thermal_var_mfrr_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="mfrr_up"]
    thermal_var_tertiary2_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary2_up"]
    thermal_var_tertiary2_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary2_down"]
    

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
        ensemble_valeur_semaine[thermal_cluster]["nb_on"] = list(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])
        [nom_noeud,nom_cluster] = thermal_cluster.split("_",1)
        nom_cluster_espace = nom_cluster.replace("*"," ")


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
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_up_tertiary2_on"] = list(thermal_var_tertiary2_up_on.loc[thermal_var_tertiary2_up_on["cluster_name"]==thermal_cluster]["sol"])
        if ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_down"][0] != 0:
            ensemble_valeur_semaine[thermal_cluster]["generation_reserve_down_tertiary2"] = list(thermal_var_tertiary2_down_on.loc[thermal_var_tertiary2_down_on["cluster_name"]==thermal_cluster]["sol"])
      

        
        if nom_cluster == "FR_VE_inj":
            disponibilite_puissance = np.array([1] * 168)
        else:
            disponibilite_puissance = np.loadtxt(study_path +  "/input/thermal/series/"+ nom_noeud +"/" + nom_cluster_espace + "/series.txt")[week*168:(week+1)*168,0]
        ensemble_valeur_semaine[thermal_cluster]["max_generating"] = disponibilite_puissance
        ensemble_valeur_semaine[thermal_cluster]["nb_units_max_invisible"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["ub"])
        ensemble_valeur_semaine[thermal_cluster]["nb_units_max"] = ensemble_valeur_semaine[thermal_cluster]["nb_units_max_invisible"]




    # for thermal_cluster in list_cluster_fr: 
    #     de_accurate_base = pd.DataFrame(data = {"energy_generation":ensemble_valeurs[thermal_cluster]["energy_generation"],
    #                                             "nodu":ensemble_valeurs[thermal_cluster]["nb_on"],
    #                                             "generation_reserve_up_primary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"],
    #                                             "generation_reserve_down_primary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"],
    #                                             "generation_reserve_up_secondary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"],
    #                                             "generation_reserve_down_secondary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"],
    #                                             "generation_reserve_up_tertiary1_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"],
    #                                             "generation_reserve_down_tertiary1":ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"],
    #                                             "generation_reserve_up_tertiary1_off":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"]})
    #     de_accurate_base.to_csv("result_step1" + thermal_cluster.replace("*","_") + ".csv",index=False)





    heuristique_resultat = {}
    nbr_heuristique = {}
    nbr_on_final = {}


    for thermal_cluster in list_thermal_clusters:
        if not(thermal_cluster in list_cluster_fr):
            nbr_on_post_optim = thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"]
            nbr_on_arrondi = list(np.ceil(nbr_on_post_optim))
            
            if thermal_cluster in ensemble_dmins_etranger:
                ensemble_dmins_etranger[thermal_cluster]["nb_units_max"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["ub"])
                nbr_on_final[thermal_cluster] = heuristique_dmin(ensemble_dmins_etranger,nbr_on_arrondi)
            else:
                nbr_on_final[thermal_cluster] = nbr_on_arrondi



            id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
            for hour, id in enumerate(id_var):
                change_lower_bound(var,id,nbr_on_final[thermal_cluster][hour])
                # change_upper_bound(var,id,nbr_on_final[thermal_cluster][hour])



    for thermal_cluster in list_cluster_fr:

        ensemble_valeurs = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]

        heuristique_resultat[thermal_cluster] = old_heuristique(
            [t for t in range(168)],
            ensemble_valeurs,
            # "perte",    # version
            # "choix", # option
            # "réduction", # bonus
            )
        
        nbr_heuristique[thermal_cluster] = []
        for t in range(168):
            nbr_heuristique[thermal_cluster].append(heuristique_resultat[thermal_cluster][t][0])

        # if (ensemble_valeurs["dmin_up"] == 1) and (ensemble_valeurs["dmin_down"] == 1):
        #     nbr_on_final[thermal_cluster] = nbr_heuristique[thermal_cluster]
        # else:
            
        nbr_on_final[thermal_cluster] = heuristique_dmin(ensemble_valeurs,nbr_heuristique[thermal_cluster])


        id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
        for hour, id in enumerate(id_var):
            change_lower_bound(var,id,ceil(nbr_on_final[thermal_cluster][hour]))
            # change_upper_bound(var,id,ceil(nbr_on_final[thermal_cluster][hour]))
    

    # de_accurate_heuristique = pd.DataFrame(data = nbr_heuristique)
    # de_accurate_heuristique.to_csv("result_mps_heuristique.csv",index=False)

    # lp_format = m.ExportModelAsLpFormat(False)
    # with open("model_2.lp","w") as file:
    #     file.write(lp_format)

    # load_basis(m,basis)
    solve_complete_problem(m)
    b = m.Iterations()
 

    
    cost2 = m.Objective().Value()


    # cost = [cost1,cost2]
    return cost2


    # de_accurate_base = pd.DataFrame(data = {"Fonction_objectif":cost})
    # de_accurate_base.to_csv("result_mps.csv",index=False)


    # thermal_var_production = find_thermal_var(m,"DispatchableProduction")
    # thermal_var_nodu = find_thermal_var(m,"NODU")

    # thermal_var_reserves_on = find_thermal_var(m,"ParticipationOfRunningUnitsToReserve")
    # thermal_var_fcr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_up"]
    # thermal_var_fcr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="fcr_down"]
    # thermal_var_afrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_up"]
    # thermal_var_afrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="afrr_down"]
    # thermal_var_mfrr_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_up"]
    # thermal_var_mfrr_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="mfrr_down"]
    # thermal_var_reserves_off = find_thermal_var(m,"ParticipationOfOffUnitsToReserve")
    # thermal_var_mfrr_up_off=thermal_var_reserves_off.loc[thermal_var_reserves_off["reserve_name"]=="mfrr_up"]
    # thermal_var_tertiary2_up_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary2_up"]
    # thermal_var_tertiary2_down_on=thermal_var_reserves_on.loc[thermal_var_reserves_on["reserve_name"]=="tertiary2_down"]
    


    # for thermal_cluster in list_cluster_fr:
    #     ensemble_valeurs[thermal_cluster]["energy_generation"] = list(thermal_var_production.loc[thermal_var_production["cluster_name"]==thermal_cluster]["sol"])
    #     ensemble_valeurs[thermal_cluster]["nb_on"] = list(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"])
    #     [nom_noeud,nom_cluster] = thermal_cluster.split("_",1)
    #     nom_cluster_espace = nom_cluster.replace("*"," ")
    #     if (nom_cluster_espace in reserve_cluster["fcr_up"]):
    #         ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"] = list(thermal_var_fcr_up_on.loc[thermal_var_fcr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     if (nom_cluster_espace in reserve_cluster["fcr_down"]):
    #         ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"] = list(thermal_var_fcr_down_on.loc[thermal_var_fcr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     if (nom_cluster_espace in reserve_cluster["mfrr_up"]):
    #         ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"] = list(thermal_var_mfrr_up_on.loc[thermal_var_mfrr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     if (nom_cluster_espace in reserve_cluster["mfrr_down"]):
    #         ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"] = list(thermal_var_mfrr_down_on.loc[thermal_var_mfrr_down_on["cluster_name"]==thermal_cluster]["sol"])
    #     if (nom_cluster_espace in reserve_cluster["mfrr_up"]) and ('max-power-off' in reserve_cluster["mfrr_up"][nom_cluster_espace]):
    #         ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"] = list(thermal_var_mfrr_up_off.loc[thermal_var_mfrr_up_off["cluster_name"]==thermal_cluster]["sol"])
    #     if (nom_cluster_espace in reserve_cluster["afrr_up"]):
    #         ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"] = list(thermal_var_afrr_up_on.loc[thermal_var_afrr_up_on["cluster_name"]==thermal_cluster]["sol"])
    #     if (nom_cluster_espace in reserve_cluster["afrr_down"]):
    #         ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"] = list(thermal_var_afrr_down_on.loc[thermal_var_afrr_down_on["cluster_name"]==thermal_cluster]["sol"])
 
    #     de_accurate_peak = pd.DataFrame(data = {"energy_generation":ensemble_valeurs[thermal_cluster]["energy_generation"],
    #                                             "nodu":ensemble_valeurs[thermal_cluster]["nb_on"],
    #                                             "generation_reserve_up_primary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"],
    #                                             "generation_reserve_down_primary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"],
    #                                             "generation_reserve_up_secondary_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"],
    #                                             "generation_reserve_down_secondary":ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"],
    #                                             "generation_reserve_up_tertiary1_on":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"],
    #                                             "generation_reserve_down_tertiary1":ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"],
    #                                             "generation_reserve_up_tertiary1_off":ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"]})
    #     de_accurate_peak.to_csv("result_step2" + thermal_cluster.replace("*","_") + ".csv",index=False)

    # somme = {}
    # somme["energy_generation"] = [ 0 ] * 168
    # somme["generation_reserve_up_primary_on"] = [ 0 ] * 168
    # somme["generation_reserve_down_primary"] = [ 0 ] * 168
    # somme["generation_reserve_up_secondary_on"] = [ 0 ] * 168
    # somme["generation_reserve_down_secondary"] = [ 0 ] * 168
    # somme["generation_reserve_up_tertiary1_on"] = [ 0 ] * 168
    # somme["generation_reserve_down_tertiary1"] = [ 0 ] * 168
    # for thermal_cluster in list_cluster_fr:
    #     for t in range(168):
    #         somme["energy_generation"][t] += ensemble_valeurs[thermal_cluster]["energy_generation"][t]
    #         somme["generation_reserve_up_primary_on"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_up_primary_on"][t]
    #         somme["generation_reserve_down_primary"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_down_primary"][t]
    #         somme["generation_reserve_up_secondary_on"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_up_secondary_on"][t]
    #         somme["generation_reserve_down_secondary"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_down_secondary"][t]
    #         somme["generation_reserve_up_tertiary1_on"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_on"][t]
    #         somme["generation_reserve_down_tertiary1"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_down_tertiary1"][t]
    #         somme["generation_reserve_up_tertiary1_on"][t] += ensemble_valeurs[thermal_cluster]["generation_reserve_up_tertiary1_off"][t]

    # de_accurate_somme = pd.DataFrame(data = somme)
    # de_accurate_somme.to_csv("result_step2_somme" + ".csv",index=False)