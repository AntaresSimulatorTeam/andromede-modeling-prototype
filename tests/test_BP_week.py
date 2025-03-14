from tests.generate_mps_files import *
from math import ceil
import numpy as np
from tests.functional.libs.heuristique import *


import time

from tests.bloc_BP_week.fonctions_week import *



def BP_week_accurate(output_path,ensemble_valeur_annuel,ensemble_dmins_etranger,week,bases):

    temps_initial = time.perf_counter()

    m = read_mps(output_path,505,week,"XPRESS_LP")
    
    
    temps_post_read_mps = time.perf_counter()


    var = m.variables()
    contraintes = m.constraints()
    delete_constraint(contraintes, 168*3, 'POffUnitsLowerBound::area<fr>:')

    changement_contrainte_eteint(var,m)
        

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




    (thermal_var_production,thermal_var_nodu,thermal_var_reserves_on,thermal_var_reserves_off,thermal_var_nodu_off) = find_var(var,["DispatchableProduction","NODU","ParticipationOfRunningUnitsToReserve","ParticipationOfOffUnitsToReserve","NumberOfOffUnitsParticipatingToReserve"])
    thermal_var_nodu_off_mfrr=thermal_var_nodu_off.loc[thermal_var_nodu_off["reserve_name"]=="mfrr_up"]
    thermal_var_nodu_off_rr=thermal_var_nodu_off.loc[thermal_var_nodu_off["reserve_name"]=="new_rr_up"]
    
    list_thermal_clusters = thermal_var_production.cluster_name.unique()

    list_cluster_fr = []
    list_cluster_etranger = []
    for thermal_cluster in list_thermal_clusters:
        [nom_noeud,nom_cluster] = thermal_cluster.split("_",1)
        if nom_noeud == "fr":
            list_cluster_fr.append(thermal_cluster)
        else:
            list_cluster_etranger.append(thermal_cluster)

    temps_lecture_resultat = time.perf_counter()

    ensemble_valeur_semaine = lecture_resultat_semaine(thermal_var_production,thermal_var_nodu,thermal_var_reserves_on,thermal_var_reserves_off,thermal_var_nodu_off,list_cluster_fr,ensemble_valeur_annuel)
    temps_ensemble_valeur_semaine_fr = time.perf_counter()


    affichage_valeur_hebdomadaire(ensemble_valeur_annuel,ensemble_valeur_semaine,list_cluster_fr,"result_step1_")

    
    nbr_heuristique = {}
    nbr_on_final = {}
    nbr_off_final = {}
    nbr_off_final["fcr"] = {}
    nbr_off_final["afrr"] = {}
    nbr_off_final["mfrr"] = {}
    nbr_off_final["rr"] = {}




    for thermal_cluster in list_thermal_clusters:
        if not(thermal_cluster in list_cluster_fr):
            nbr_on_post_optim = round(thermal_var_nodu[thermal_var_nodu["cluster_name"]==thermal_cluster]["sol"],6)
            nbr_heuristique[thermal_cluster] = list(np.ceil(nbr_on_post_optim))

    temps_heuristique_arrondi_etranger = time.perf_counter()



    for thermal_cluster in list_thermal_clusters:
        if not(thermal_cluster in list_cluster_fr):
            if (thermal_cluster in ensemble_dmins_etranger) and (nbr_heuristique[thermal_cluster] != list([float(0)] * 168)):
                ensemble_dmins_etranger[thermal_cluster]["nb_units_max"] = list(thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster]["ub"])
                nbr_on_final[thermal_cluster] = heuristique_dmin_accurate(ensemble_dmins_etranger[thermal_cluster],nbr_heuristique[thermal_cluster])
            else:
                nbr_on_final[thermal_cluster] = nbr_heuristique[thermal_cluster]

    temps_heuristique_dmin_etranger = time.perf_counter()


    changement_bornes(list_cluster_etranger,thermal_var_nodu,var,nbr_on_final)
    temps_changement_borne_etranger = time.perf_counter()





    nbr_heuristique = resolution_heuristique_arrondi(list_cluster_fr,ensemble_valeur_annuel,ensemble_valeur_semaine,nbr_heuristique,old_heuristique)
    temps_heuristique_arrondi_fr_old = time.perf_counter()

    nbr_on_final = resolution_heuristique_Dmin(list_cluster_fr,ensemble_valeur_annuel,ensemble_valeur_semaine,nbr_heuristique,nbr_on_final)
    temps_heuristique_dmin_fr_old = time.perf_counter()


    # nbr_off_final = resolution_heuristique_arrondi_eteint(list_cluster_fr,ensemble_valeur_annuel,ensemble_valeur_semaine,nbr_off_final,nbr_on_final,heuristique_eteint_mutualise,option ="quantite",bonus = " ")
    # changement_bornes(list_cluster_fr,thermal_var_nodu_off_mfrr,var,nbr_off_final["mfrr"])
    # changement_bornes(list_cluster_fr,thermal_var_nodu_off_rr,var,nbr_off_final["rr"])
    temps_heuristique_eteint_old = time.perf_counter()


    changement_bornes(list_cluster_fr,thermal_var_nodu,var,nbr_on_final)
    temps_changement_borne_fr_old = time.perf_counter()


    # de_accurate_heuristique = pd.DataFrame(data = nbr_heuristique)
    # de_accurate_heuristique.to_csv("result_mps_heuristique_old.csv",index=False)


    # de_accurate_heuristique = pd.DataFrame(data = nbr_off_final)
    # de_accurate_heuristique.to_csv("result_nbr_off_old.csv",index=False)

    solve_complete_problem(m)
 
    cost_old = m.Objective().Value()

    temps_post_opti2_old = time.perf_counter()

    (heure_defaillance_old,quantite_defaillance_old) = lecture_resultat_defaillance(var)
    
    
    load_basis(m,bases)

    temps_post_defaillace_old = time.perf_counter()




    # for thermal_cluster in list_cluster_fr:
    #     ensemble_valeurs = ensemble_valeur_annuel[thermal_cluster] | ensemble_valeur_semaine[thermal_cluster]

    #     heuristique_resultat = heuristique_opti_repartition_sans_pmin(
    #         [t for t in range(168)],
    #         ensemble_valeurs,
    #         "choix",    # version
    #         # "quantite", # option
    #         # " ", # bonus
    #         )
        
    #     nbr_heuristique[thermal_cluster] = []
    #     for t in range(168):
    #         nbr_heuristique[thermal_cluster].append(heuristique_resultat[t][0])
    
    nbr_heuristique = resolution_heuristique_arrondi(list_cluster_fr,ensemble_valeur_annuel,ensemble_valeur_semaine,nbr_heuristique,heuristique_opti_repartition_sans_pmin,version="choix")
    temps_heuristique_arrondi_fr_new = time.perf_counter()

    nbr_on_final = resolution_heuristique_Dmin(list_cluster_fr,ensemble_valeur_annuel,ensemble_valeur_semaine,nbr_heuristique,nbr_on_final)
    temps_heuristique_dmin_fr_new = time.perf_counter()


    # nbr_off_final = resolution_heuristique_arrondi_eteint(list_cluster_fr,ensemble_valeur_annuel,ensemble_valeur_semaine,nbr_off_final,nbr_on_final,heuristique_eteint_mutualise,option ="quantite",bonus = " ")
    # changement_bornes(list_cluster_fr,thermal_var_nodu_off_mfrr,var,nbr_off_final["mfrr"])
    # changement_bornes(list_cluster_fr,thermal_var_nodu_off_rr,var,nbr_off_final["rr"])
    temps_heuristique_eteint_new = time.perf_counter()

    changement_bornes(list_cluster_fr,thermal_var_nodu,var,nbr_on_final)
    temps_changement_borne_fr_new = time.perf_counter()



    # de_accurate_heuristique = pd.DataFrame(data = nbr_heuristique)
    # de_accurate_heuristique.to_csv("result_mps_heuristique_new.csv",index=False)

    # de_accurate_heuristique = pd.DataFrame(data = nbr_off_final)
    # de_accurate_heuristique.to_csv("result_nbr_off_new.csv",index=False)



    solve_complete_problem(m)
    cost_new = m.Objective().Value()

    temps_post_opti2_new = time.perf_counter()

    (heure_defaillance,quantite_defaillance) = lecture_resultat_defaillance(var)


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
             temps_heuristique_eteint_old - temps_heuristique_dmin_fr_old,
             temps_changement_borne_fr_old - temps_heuristique_eteint_old,
             temps_post_opti2_old-temps_changement_borne_fr_old,
             temps_heuristique_arrondi_fr_new -temps_post_defaillace_old,
             temps_heuristique_dmin_fr_new - temps_heuristique_arrondi_fr_new,
             temps_heuristique_eteint_new-temps_heuristique_dmin_fr_new,
             temps_changement_borne_fr_new-temps_heuristique_eteint_new,
             temps_post_opti2_new-temps_changement_borne_fr_new
             ]
    
    
    # (thermal_var_production,thermal_var_nodu,thermal_var_reserves_on,thermal_var_reserves_off,thermal_var_nodu_off) = find_var(var,["DispatchableProduction","NODU","ParticipationOfRunningUnitsToReserve","ParticipationOfOffUnitsToReserve","NumberOfOffUnitsParticipatingToReserve"])
    # ensemble_valeur_semaine = lecture_resultat_semaine(thermal_var_production,thermal_var_nodu,thermal_var_reserves_on,thermal_var_reserves_off,thermal_var_nodu_off,list_cluster_fr,ensemble_valeur_annuel)
    
    # affichage_valeur_hebdomadaire(ensemble_valeur_annuel,ensemble_valeur_semaine,list_cluster_fr,"result_step2")


    return (cost,temps,heure_defaillance_old,quantite_defaillance_old,heure_defaillance,quantite_defaillance,bases)



def BP_week_milp(output_path,week):

    temps_initial = time.perf_counter()


    m = read_mps(output_path,505,week,"XPRESS")    
    temps_post_read_mps = time.perf_counter()


    contraintes = m.constraints()
    var = m.variables()
    delete_constraint(contraintes, 168*3, 'POffUnitsLowerBound::area<fr>:')

    changement_contrainte_eteint(var,m)


    milp_version(m)

    # interger_vars = [
    #     i
    #     for i in range(len(var))
    #     if var[i].name().strip().split("::")[0]
    #     in [
    #         "NumberOfOffUnitsParticipatingToReserve",
    #     ]
    # ]
    # for i in interger_vars:
    #     var[i].SetInteger(True)


    # lp_format = m.ExportModelAsLpFormat(False)
    # with open("model_milp.lp","w") as file:
    #     file.write(lp_format)  


    
    temps_conversion_milp = time.perf_counter()

    solve_complete_problem(m)

    cost = m.Objective().Value()

    temps_post_optim = time.perf_counter()

    (heure_defaillance,quantite_defaillance) = lecture_resultat_defaillance(var)


    # thermal_var_nodu = find_var(var,["NODU"])[0]

    # list_thermal_clusters = thermal_var_nodu.cluster_name.unique()
    # list_cluster_fr = []
    # for thermal_cluster in list_thermal_clusters:
    #     [nom_noeud,nom_cluster] = thermal_cluster.split("_",1)
    #     if nom_noeud == "fr":
    #         list_cluster_fr.append(thermal_cluster)
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

    # changement_contrainte_eteint(var,m)


    var_id = [i for i in range(len(var)) if 'NODU::area<' in var[i].name()]
    assert len(var_id) in [0, 168*nbr_thermal_clusters]
    if len(var_id) == 168*nbr_thermal_clusters:
        for i in var_id:
            m.Objective().SetCoefficient(var[i], 0)


    temps_conversion_fast = time.perf_counter()


    # lp_format = m.ExportModelAsLpFormat(False)
    # with open("model_fast_complexe.lp","w") as file:
    #     file.write(lp_format)    

    if bases != None:
        load_basis(m,bases)

    temps_load_bases = time.perf_counter()


    solve_complete_problem(m)

    cost1 = m.Objective().Value()


    temps_post_opti1 = time.perf_counter()


    bases = get_basis(m)
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

    # affichage_valeur_hebdomadaire({},ensemble_valeur_semaine,list_cluster_fr,"result_step1")

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


 
    for thermal_cluster in list_thermal_clusters:
        cout_nodu += nbr_on_final[thermal_cluster][0] * ensemble_valeur_annuel[thermal_cluster]["fixed_cost"]
        for t in range(1,168):
            cout_nodu += nbr_on_final[thermal_cluster][t] * ensemble_valeur_annuel[thermal_cluster]["fixed_cost"]
            if nbr_on_final[thermal_cluster][t] > nbr_on_final[thermal_cluster][t-1]:
                cout_nodu += (nbr_on_final[thermal_cluster][t]-nbr_on_final[thermal_cluster][t-1]) * ensemble_valeur_annuel[thermal_cluster]["startup_cost"]

        
        id_var = thermal_var_nodu.loc[thermal_var_nodu["cluster_name"]==thermal_cluster,"id_var"]
        for hour, id in enumerate(id_var):
            change_lower_bound(var,id,nbr_on_final[thermal_cluster][hour])
            change_upper_bound(var,id,nbr_on_final[thermal_cluster][hour])


        

        # nbr_off_float = [[ensemble_valeur_semaine[thermal_cluster]["nb_off_mfrr"][t],ensemble_valeur_semaine[thermal_cluster]["nb_off_rr"][t]] for t in range(168)]
        # nbr_off[thermal_cluster] = []
        # for t in range(168):
        #     nbr_on = nbr_on_final[thermal_cluster][t]
        #     nbr_units_max = ensemble_valeur_semaine[thermal_cluster]["nb_units_max"][t]
        #     nbr_off_t = [min(ceil(round(nbr_off_float[t][0],12)),nbr_units_max-nbr_on),min(ceil(round(nbr_off_float[t][1],12)),nbr_units_max-nbr_on)]
        #     p_min = ensemble_valeur_annuel[thermal_cluster]["p_min"]
        #     p_max = ensemble_valeur_annuel[thermal_cluster]["p_max"]
        #     participation_max_off = [ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary1_reserve_up_off"],ensemble_valeur_annuel[thermal_cluster]["participation_max_tertiary2_reserve_up_off"]]
        #     while sum(nbr_off_t) * p_min > p_max * (nbr_units_max - nbr_on):
        #             premier_indice_non_nulle = 0
        #             while nbr_off_t[premier_indice_non_nulle] == 0 :
        #                 premier_indice_non_nulle += 1
        #             quantite_mini = participation_max_off[premier_indice_non_nulle] * min(nbr_off_float[premier_indice_non_nulle]-(nbr_off_t[premier_indice_non_nulle]-1),nbr_off_t[premier_indice_non_nulle])
        #             indice_mini = premier_indice_non_nulle
        #             for i in range(premier_indice_non_nulle+1,len(nbr_off_t)):
        #                 quantite = participation_max_off[i] * min(nbr_off_float[i]-(nbr_off_t[i]-1),nbr_off_t[i])
        #                 if (nbr_off_t[i] != 0) and (quantite <= quantite_mini):
        #                     indice_mini = i
        #                     quantite_mini = quantite
        #             nbr_off_t[indice_mini] -= 1
        #     nbr_off[thermal_cluster].append(nbr_off_t) 

        # id_var = thermal_var_nodu_off_mfrr.loc[thermal_var_nodu_off_mfrr["cluster_name"]==thermal_cluster,"id_var"]
        # for hour, id in enumerate(id_var):
        #     change_lower_bound(var,id,nbr_off[thermal_cluster][hour][0])
        #     change_upper_bound(var,id,nbr_off[thermal_cluster][hour][0])
        # id_var = thermal_var_nodu_off_rr.loc[thermal_var_nodu_off_rr["cluster_name"]==thermal_cluster,"id_var"]
        # for hour, id in enumerate(id_var):
        #     change_lower_bound(var,id,nbr_off[thermal_cluster][hour][1])
        #     change_upper_bound(var,id,nbr_off[thermal_cluster][hour][1])



    temps_changement_borne = time.perf_counter()

    # lp_format = m.ExportModelAsLpFormat(False)
    # with open("model_fast_2.lp","w") as file:
    #     file.write(lp_format)


    solve_complete_problem(m)
    cost2 = m.Objective().Value()

    temps_post_opti2 = time.perf_counter()

    (heure_defaillance,quantite_defaillance) = lecture_resultat_defaillance(var)

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

    # affichage_valeur_hebdomadaire({},ensemble_valeur_semaine,list_cluster_fr,"result_step2")


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

    # affichage_valeur_hebdomadaire({},ensemble_valeur_semaine,list_cluster_fr,"result_step1")

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

    cost2 = m.Objective().Value()
    temps_post_opti2 = time.perf_counter()
 

    (heure_defaillance,quantite_defaillance) = lecture_resultat_defaillance(var)


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

    # affichage_valeur_hebdomadaire({},ensemble_valeur_semaine,list_cluster_fr,"result_step2")


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