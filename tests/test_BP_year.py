from tests.test_BP_week import (BP_week_accurate,BP_week_milp,BP_week_fast_eteint,BP_week_fast_simple,lecture_donnees_accurate,lecture_donnees_fast)
import time
import pandas as pd
from tests.generate_mps_files import *

def test_BP_year_accurate():

    study_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_4_reserves"
    antares_path = "D:/AppliRTE/bin/antares-solver.exe"
    # output_path = generate_mps_file(study_path,antares_path)
    # output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_mfrr_FR_1_week/output/20250130-0937exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_FR_1week_eteint/output/20250127-1411exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_REF_accurate_sans_reserves/output/20250203-1735exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_REF_accurate_reserves/output/20250211-1334exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_REF_4reserves/output/20250214-0944exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_version_kth/output/20250219-1439exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_final_version_kth/output/20250221-1509exp-export_mps"    
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_new_4reserves/output/20250303-1357exp-export_mps"   
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_base_sans_reserves_an_55/output/20250305-1149exp-export_mps-2"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_3_reserves/output/20250305-1514exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_0_reserves/output/20250305-2102exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_3_reserves++/output/20250307-1529exp-export_mps"
    output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_4_reserves/output/20250310-1400exp-export_mps"



    cost_step1 = []
    cost_old = []
    cost_heuristique = []
    temps_lecture_mps = []
    temps_lecture_var = []
    temps_load_bases = []
    temps_opti1 = []
    temps_get_bases = []
    temps_lecture_resultat = []
    temps_creation_ensemble_semaine_fr = []
    temps_heuristique_arrondi_etranger = []
    temps_heuristique_dmin_etranger = []
    temps_heuristique_eteint_old = []
    temps_changement_borne_etranger = []
    temps_heuristique_arrondi_fr_old = []
    temps_heuristique_dmin_fr_old = []
    temps_changement_borne_fr_old = []
    temps_opti2_old = []
    temps_heuristique_arrondi_fr_new = []
    temps_heuristique_dmin_fr_new = []
    temps_changement_borne_fr_new = []
    temps_heuristique_eteint_new = []
    temps_opti2_new = []
    temps_total = []
    heure_defaillance_prod_old = []
    heure_defaillance_fcr_up_old = []
    heure_defaillance_fcr_down_old = []
    heure_defaillance_afrr_up_old = []
    heure_defaillance_affr_down_old = []
    heure_defaillance_mfrr_up_old = []
    heure_defaillance_mfrr_down_old = []
    heure_defaillance_rr_up_old = []
    heure_defaillance_rr_down_old = []
    quantite_defaillance_prod_old = []
    quantite_defaillance_fcr_up_old = []
    quantite_defaillance_fcr_down_old = []
    quantite_defaillance_afrr_up_old = []
    quantite_defaillance_affr_down_old = []
    quantite_defaillance_mfrr_up_old = []
    quantite_defaillance_mfrr_down_old = []
    quantite_defaillance_rr_up_old = []
    quantite_defaillance_rr_down_old = []
    heure_defaillance_prod = []
    heure_defaillance_fcr_up = []
    heure_defaillance_fcr_down = []
    heure_defaillance_afrr_up = []
    heure_defaillance_affr_down = []
    heure_defaillance_mfrr_up = []
    heure_defaillance_mfrr_down = []
    heure_defaillance_rr_up = []
    heure_defaillance_rr_down = []
    quantite_defaillance_prod = []
    quantite_defaillance_fcr_up = []
    quantite_defaillance_fcr_down = []
    quantite_defaillance_afrr_up = []
    quantite_defaillance_affr_down = []
    quantite_defaillance_mfrr_up = []
    quantite_defaillance_mfrr_down = []
    quantite_defaillance_rr_up = []
    quantite_defaillance_rr_down = []
    bases = None

    (ensemble_valeur_annuel,ensemble_dmins_etranger) = lecture_donnees_accurate(study_path)

    for week in range(52):
        temps_initial = time.perf_counter()
        (costs,temps,heure_defaillance_old,quantite_defaillance_old,heure_defaillance,quantite_defaillance,bases) = BP_week_accurate(output_path,ensemble_valeur_annuel,ensemble_dmins_etranger,week,bases)
        temps_actuel = time.perf_counter() 
        temps_total.append(temps_actuel - temps_initial)
        cost_step1.append(costs[0])
        cost_old.append(costs[1])
        cost_heuristique.append(costs[2])
        temps_lecture_mps.append(temps[0])
        temps_lecture_var.append(temps[1])
        temps_load_bases.append(temps[2])
        temps_opti1.append(temps[3])
        temps_get_bases.append(temps[4])
        temps_lecture_resultat.append(temps[5])
        temps_creation_ensemble_semaine_fr.append(temps[6])
        temps_heuristique_arrondi_etranger.append(temps[7])
        temps_heuristique_dmin_etranger.append(temps[8])
        temps_changement_borne_etranger.append(temps[9])
        temps_heuristique_arrondi_fr_old.append(temps[10])
        temps_heuristique_dmin_fr_old.append(temps[11])
        temps_heuristique_eteint_old.append(temps[12])
        temps_changement_borne_fr_old.append(temps[13])
        temps_opti2_old.append(temps[14])
        temps_heuristique_arrondi_fr_new.append(temps[15])
        temps_heuristique_dmin_fr_new.append(temps[16])
        temps_heuristique_eteint_new.append(temps[17])
        temps_changement_borne_fr_new.append(temps[18])
        temps_opti2_new.append(temps[19])
        heure_defaillance_prod_old.append(heure_defaillance_old[0])
        heure_defaillance_fcr_up_old.append(heure_defaillance_old[1])
        heure_defaillance_fcr_down_old.append(heure_defaillance_old[2])
        heure_defaillance_afrr_up_old.append(heure_defaillance_old[3])
        heure_defaillance_affr_down_old.append(heure_defaillance_old[4])
        heure_defaillance_mfrr_up_old.append(heure_defaillance_old[5])
        heure_defaillance_mfrr_down_old.append(heure_defaillance_old[6])
        heure_defaillance_rr_up_old.append(heure_defaillance_old[7])
        heure_defaillance_rr_down_old.append(heure_defaillance_old[8])
        quantite_defaillance_prod_old.append(quantite_defaillance_old[0])
        quantite_defaillance_fcr_up_old.append(quantite_defaillance_old[1])
        quantite_defaillance_fcr_down_old.append(quantite_defaillance_old[2])
        quantite_defaillance_afrr_up_old.append(quantite_defaillance_old[3])
        quantite_defaillance_affr_down_old.append(quantite_defaillance_old[4])
        quantite_defaillance_mfrr_up_old.append(quantite_defaillance_old[5])
        quantite_defaillance_mfrr_down_old.append(quantite_defaillance_old[6])
        quantite_defaillance_rr_up_old.append(quantite_defaillance_old[7])
        quantite_defaillance_rr_down_old.append(quantite_defaillance_old[8])
        heure_defaillance_prod.append(heure_defaillance[0])
        heure_defaillance_fcr_up.append(heure_defaillance[1])
        heure_defaillance_fcr_down.append(heure_defaillance[2])
        heure_defaillance_afrr_up.append(heure_defaillance[3])
        heure_defaillance_affr_down.append(heure_defaillance[4])
        heure_defaillance_mfrr_up.append(heure_defaillance[5])
        heure_defaillance_mfrr_down.append(heure_defaillance[6])
        heure_defaillance_rr_up.append(heure_defaillance[7])
        heure_defaillance_rr_down.append(heure_defaillance[8])
        quantite_defaillance_prod.append(quantite_defaillance[0])
        quantite_defaillance_fcr_up.append(quantite_defaillance[1])
        quantite_defaillance_fcr_down.append(quantite_defaillance[2])
        quantite_defaillance_afrr_up.append(quantite_defaillance[3])
        quantite_defaillance_affr_down.append(quantite_defaillance[4])
        quantite_defaillance_mfrr_up.append(quantite_defaillance[5])
        quantite_defaillance_mfrr_down.append(quantite_defaillance[6])
        quantite_defaillance_rr_up.append(quantite_defaillance[7])
        quantite_defaillance_rr_down.append(quantite_defaillance[8])

    de_BP_year = pd.DataFrame(data = {
        "Optim_1":cost_step1,"old_heuristique":cost_old,"new_heuristique":cost_heuristique,
        "temps_total":temps_total,
        "temps_lecture_mps": temps_lecture_mps ,
        "temps_lecture_var": temps_lecture_var ,
        "temps_load_bases":temps_load_bases,
        "temps_opti1": temps_opti1 ,
        "temps_get_bases":temps_get_bases,
        "temps_lecture_resultat": temps_lecture_resultat ,
        "temps_creation_ensemble_semaine_fr": temps_creation_ensemble_semaine_fr ,
        "temps_heuristique_arrondi_etranger": temps_heuristique_arrondi_etranger ,
        "temps_heuristique_dmin_etranger": temps_heuristique_dmin_etranger ,
        "temps_changement_borne_etranger": temps_changement_borne_etranger ,
        "temps_heuristique_arrondi_fr_old": temps_heuristique_arrondi_fr_old,
        "temps_heuristique_dmin_fr_old": temps_heuristique_dmin_fr_old,
        "temps_changement_borne_fr_old": temps_changement_borne_fr_old,
        "temps_heuristique_eteint_old" : temps_heuristique_eteint_old,
        "temps_opti2_old": temps_opti2_old,
        "temps_heuristique_arrondi_fr": temps_heuristique_arrondi_fr_new,
        "temps_heuristique_dmin_fr_new": temps_heuristique_dmin_fr_new,
        "temps_changement_borne_fr_new": temps_changement_borne_fr_new,
        "temps_heuristique_eteint_new" : temps_heuristique_eteint_new,
        "temps_opti2_new": temps_opti2_new,
        "heure_defaillance_prod_old": heure_defaillance_prod_old,
        "heure_defaillance_fcr_up_old":  heure_defaillance_fcr_up_old,
        "heure_defaillance_fcr_down_old": heure_defaillance_fcr_down_old ,
        "heure_defaillance_afrr_up_old": heure_defaillance_afrr_up_old ,
        "heure_defaillance_affr_down_old": heure_defaillance_affr_down_old ,
        "heure_defaillance_mfrr_up_old": heure_defaillance_mfrr_up_old,
        "heure_defaillance_mfrr_down_old": heure_defaillance_mfrr_down_old ,
        "heure_defaillance_rr_up_old":heure_defaillance_rr_up_old  ,
        "heure_defaillance_rr_down_old":heure_defaillance_rr_down_old  ,
        "quantite_defaillance_prod_old": quantite_defaillance_prod_old,
        "quantite_defaillance_fcr_up_old":  quantite_defaillance_fcr_up_old,
        "quantite_defaillance_fcr_down_old": quantite_defaillance_fcr_down_old ,
        "quantite_defaillance_afrr_up_old": quantite_defaillance_afrr_up_old ,
        "quantite_defaillance_affr_down_old": quantite_defaillance_affr_down_old ,
        "quantite_defaillance_mfrr_up_old": quantite_defaillance_mfrr_up_old,
        "quantite_defaillance_mfrr_down_old": quantite_defaillance_mfrr_down_old ,
        "quantite_defaillance_rr_up_old":quantite_defaillance_rr_up_old  ,
        "quantite_defaillance_rr_down_old":quantite_defaillance_rr_down_old  ,
        "heure_defaillance_prod": heure_defaillance_prod,
        "heure_defaillance_fcr_up":  heure_defaillance_fcr_up,
        "heure_defaillance_fcr_down": heure_defaillance_fcr_down ,
        "heure_defaillance_afrr_up": heure_defaillance_afrr_up ,
        "heure_defaillance_affr_down": heure_defaillance_affr_down ,
        "heure_defaillance_mfrr_up": heure_defaillance_mfrr_up,
        "heure_defaillance_mfrr_down": heure_defaillance_mfrr_down ,
        "heure_defaillance_rr_up":heure_defaillance_rr_up  ,
        "heure_defaillance_rr_down":heure_defaillance_rr_down  ,
        "quantite_defaillance_prod": quantite_defaillance_prod,
        "quantite_defaillance_fcr_up":  quantite_defaillance_fcr_up,
        "quantite_defaillance_fcr_down": quantite_defaillance_fcr_down ,
        "quantite_defaillance_afrr_up": quantite_defaillance_afrr_up ,
        "quantite_defaillance_affr_down": quantite_defaillance_affr_down ,
        "quantite_defaillance_mfrr_up": quantite_defaillance_mfrr_up,
        "quantite_defaillance_mfrr_down": quantite_defaillance_mfrr_down ,
        "quantite_defaillance_rr_up":quantite_defaillance_rr_up  ,
        "quantite_defaillance_rr_down":quantite_defaillance_rr_down  ,
        })
    de_BP_year.to_csv("result_year_accurate.csv",index=False)


def test_BP_year_milp():

    # output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_mfrr_FR_1_week/output/20250130-0937exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_REF_accurate_sans_reserves/output/20250203-1735exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_REF_accurate_reserves/output/20250211-1334exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_version_kth/output/20250219-1439exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_final_version_kth/output/20250221-1509exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_3_reserves/output/20250305-1514exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_0_reserves/output/20250305-2102exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_3_reserves++/output/20250307-1529exp-export_mps"
    output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_4_reserves/output/20250310-1400exp-export_mps"




    week_cost = []
    temps_lecture_mps = []
    temps_conversion_milp = []
    temps_opti = []
    temps_total = []
    heure_defaillance_prod = []
    heure_defaillance_fcr_up = []
    heure_defaillance_fcr_down = []
    heure_defaillance_afrr_up = []
    heure_defaillance_affr_down = []
    heure_defaillance_mfrr_up = []
    heure_defaillance_mfrr_down = []
    heure_defaillance_rr_up = []
    heure_defaillance_rr_down = []
    quantite_defaillance_prod = []
    quantite_defaillance_fcr_up = []
    quantite_defaillance_fcr_down = []
    quantite_defaillance_afrr_up = []
    quantite_defaillance_affr_down = []
    quantite_defaillance_mfrr_up = []
    quantite_defaillance_mfrr_down = []
    quantite_defaillance_rr_up = []
    quantite_defaillance_rr_down = []

    

    temps_initial = time.perf_counter()
    for week in range(52):
        (cost_semaine,temps,heure_defaillance,quantite_defaillance) = BP_week_milp(output_path,week)
        temps_actuel = time.perf_counter() 
        temps_total.append(temps_actuel - temps_initial)
        temps_lecture_mps.append(temps[0])
        temps_conversion_milp.append(temps[1])
        temps_opti.append(temps[2])
        temps_initial = temps_actuel
        week_cost.append(cost_semaine)
        heure_defaillance_prod.append(heure_defaillance[0])
        heure_defaillance_fcr_up.append(heure_defaillance[1])
        heure_defaillance_fcr_down.append(heure_defaillance[2])
        heure_defaillance_afrr_up.append(heure_defaillance[3])
        heure_defaillance_affr_down.append(heure_defaillance[4])
        heure_defaillance_mfrr_up.append(heure_defaillance[5])
        heure_defaillance_mfrr_down.append(heure_defaillance[6])
        heure_defaillance_rr_up.append(heure_defaillance[7])
        heure_defaillance_rr_down.append(heure_defaillance[8])
        quantite_defaillance_prod.append(quantite_defaillance[0])
        quantite_defaillance_fcr_up.append(quantite_defaillance[1])
        quantite_defaillance_fcr_down.append(quantite_defaillance[2])
        quantite_defaillance_afrr_up.append(quantite_defaillance[3])
        quantite_defaillance_affr_down.append(quantite_defaillance[4])
        quantite_defaillance_mfrr_up.append(quantite_defaillance[5])
        quantite_defaillance_mfrr_down.append(quantite_defaillance[6])
        quantite_defaillance_rr_up.append(quantite_defaillance[7])
        quantite_defaillance_rr_down.append(quantite_defaillance[8])


    de_BP_year = pd.DataFrame(data = {
        "Optim_milp":week_cost,
        "Temps_total":temps_total,
        "temps_lecture_mps" : temps_lecture_mps,
        "temps_conversion_milp" : temps_conversion_milp,
        "temps_opti" : temps_opti,
        "heure_defaillance_prod": heure_defaillance_prod,
        "heure_defaillance_fcr_up":  heure_defaillance_fcr_up,
        "heure_defaillance_fcr_down": heure_defaillance_fcr_down ,
        "heure_defaillance_afrr_up": heure_defaillance_afrr_up ,
        "heure_defaillance_affr_down": heure_defaillance_affr_down ,
        "heure_defaillance_mfrr_up": heure_defaillance_mfrr_up,
        "heure_defaillance_mfrr_down": heure_defaillance_mfrr_down ,
        "heure_defaillance_rr_up":heure_defaillance_rr_up  ,
        "heure_defaillance_rr_down":heure_defaillance_rr_down  ,
        "quantite_defaillance_prod": quantite_defaillance_prod,
        "quantite_defaillance_fcr_up":  quantite_defaillance_fcr_up,
        "quantite_defaillance_fcr_down": quantite_defaillance_fcr_down ,
        "quantite_defaillance_afrr_up": quantite_defaillance_afrr_up ,
        "quantite_defaillance_affr_down": quantite_defaillance_affr_down ,
        "quantite_defaillance_mfrr_up": quantite_defaillance_mfrr_up,
        "quantite_defaillance_mfrr_down": quantite_defaillance_mfrr_down ,
        "quantite_defaillance_rr_up":quantite_defaillance_rr_up  ,
        "quantite_defaillance_rr_down":quantite_defaillance_rr_down  ,
        })
    de_BP_year.to_csv("result_year_milp.csv",index=False)


def test_BP_year_fast_eteint():

    study_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_0_reserves"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_mfrr_FR_1_week/output/20250130-0937exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_REF_accurate_sans_reserves/output/20250203-1735exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_version_kth/output/20250219-1439exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_final_version_kth/output/20250221-1509exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_3_reserves/output/20250305-1514exp-export_mps"
    output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_0_reserves/output/20250305-2102exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_3_reserves++/output/20250307-1529exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_4_reserves/output/20250310-1400exp-export_mps"

    


    cost_step1 = []
    cost_step2 = []
    cost_total_step2 = []
    temps_lecture_mps = []
    temps_conversion_fast = []
    temps_load_bases = []
    temps_opti1 = []
    temps_get_bases = []
    temps_lecture_resultat = []
    temps_creation_ensemble_semaine = []
    temps_heuristique_arrondi = []
    temps_heuristique_dmin = []
    temps_changement_borne = []
    temps_opti2 = []
    temps_total = []
    heure_defaillance_prod = []
    heure_defaillance_fcr_up = []
    heure_defaillance_fcr_down = []
    heure_defaillance_afrr_up = []
    heure_defaillance_affr_down = []
    heure_defaillance_mfrr_up = []
    heure_defaillance_mfrr_down = []
    heure_defaillance_rr_up = []
    heure_defaillance_rr_down = []
    quantite_defaillance_prod = []
    quantite_defaillance_fcr_up = []
    quantite_defaillance_fcr_down = []
    quantite_defaillance_afrr_up = []
    quantite_defaillance_affr_down = []
    quantite_defaillance_mfrr_up = []
    quantite_defaillance_mfrr_down = []
    quantite_defaillance_rr_up = []
    quantite_defaillance_rr_down = []
    bases = None

    ensemble_valeur_annuel = lecture_donnees_fast(study_path)

    temps_initial = time.perf_counter()
    for week in range(52):
        (costs,temps,heure_defaillance,quantite_defaillance,bases) = BP_week_fast_eteint(output_path,ensemble_valeur_annuel,week,bases)
        temps_actuel = time.perf_counter() 
        temps_total.append(temps_actuel - temps_initial)
        temps_lecture_mps.append(temps[0])
        temps_conversion_fast.append(temps[1])
        temps_load_bases.append(temps[2])
        temps_opti1.append(temps[3])
        temps_get_bases.append(temps[4])
        temps_lecture_resultat.append(temps[5])
        temps_creation_ensemble_semaine.append(temps[6])
        temps_heuristique_arrondi.append(temps[7])
        temps_heuristique_dmin.append(temps[8])
        temps_changement_borne.append(temps[9])
        temps_opti2.append(temps[10])
        temps_initial = temps_actuel
        cost_step1.append(costs[0])
        cost_step2.append(costs[1])
        cost_total_step2.append(costs[1]+costs[2])
        heure_defaillance_prod.append(heure_defaillance[0])
        heure_defaillance_fcr_up.append(heure_defaillance[1])
        heure_defaillance_fcr_down.append(heure_defaillance[2])
        heure_defaillance_afrr_up.append(heure_defaillance[3])
        heure_defaillance_affr_down.append(heure_defaillance[4])
        heure_defaillance_mfrr_up.append(heure_defaillance[5])
        heure_defaillance_mfrr_down.append(heure_defaillance[6])
        heure_defaillance_rr_up.append(heure_defaillance[7])
        heure_defaillance_rr_down.append(heure_defaillance[8])
        quantite_defaillance_prod.append(quantite_defaillance[0])
        quantite_defaillance_fcr_up.append(quantite_defaillance[1])
        quantite_defaillance_fcr_down.append(quantite_defaillance[2])
        quantite_defaillance_afrr_up.append(quantite_defaillance[3])
        quantite_defaillance_affr_down.append(quantite_defaillance[4])
        quantite_defaillance_mfrr_up.append(quantite_defaillance[5])
        quantite_defaillance_mfrr_down.append(quantite_defaillance[6])
        quantite_defaillance_rr_up.append(quantite_defaillance[7])
        quantite_defaillance_rr_down.append(quantite_defaillance[8])

    de_BP_year = pd.DataFrame(data = {
        "Optim_1":cost_step1,"Optim_2":cost_step2,"post-traitement":cost_total_step2,
        "temps_total":temps_total,
        "temps_lecture_mps": temps_lecture_mps,
        "temps_conversion_fast": temps_conversion_fast,
        "temps_load_bases":temps_load_bases,
        "temps_opti1": temps_opti1,
        "temps_get_bases":temps_get_bases,
        "temps_lecture_resultat": temps_lecture_resultat ,
        "temps_creation_ensemble_semaine": temps_creation_ensemble_semaine,
        "temps_heuristique_arrondi": temps_heuristique_arrondi,
        "temps_heuristique_dmin": temps_heuristique_dmin,
        "temps_changement_borne": temps_changement_borne,
        "temps_opti2": temps_opti2,
        "heure_defaillance_prod": heure_defaillance_prod,
        "heure_defaillance_fcr_up":  heure_defaillance_fcr_up,
        "heure_defaillance_fcr_down": heure_defaillance_fcr_down ,
        "heure_defaillance_afrr_up": heure_defaillance_afrr_up ,
        "heure_defaillance_affr_down": heure_defaillance_affr_down ,
        "heure_defaillance_mfrr_up": heure_defaillance_mfrr_up,
        "heure_defaillance_mfrr_down": heure_defaillance_mfrr_down ,
        "heure_defaillance_rr_up":heure_defaillance_rr_up  ,
        "heure_defaillance_rr_down":heure_defaillance_rr_down  ,
        "quantite_defaillance_prod": quantite_defaillance_prod,
        "quantite_defaillance_fcr_up":  quantite_defaillance_fcr_up,
        "quantite_defaillance_fcr_down": quantite_defaillance_fcr_down ,
        "quantite_defaillance_afrr_up": quantite_defaillance_afrr_up ,
        "quantite_defaillance_affr_down": quantite_defaillance_affr_down ,
        "quantite_defaillance_mfrr_up": quantite_defaillance_mfrr_up,
        "quantite_defaillance_mfrr_down": quantite_defaillance_mfrr_down ,
        "quantite_defaillance_rr_up":quantite_defaillance_rr_up  ,
        "quantite_defaillance_rr_down":quantite_defaillance_rr_down  ,
        })
    de_BP_year.to_csv("result_year_fast_eteint.csv",index=False)


def test_BP_year_fast_simple():

    study_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_4_reserves"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_mfrr_FR_1_week/output/20250130-0937exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_REF_accurate_sans_reserves/output/20250203-1735exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_version_kth/output/20250219-1439exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_definitifs/BP23_final_version_kth/output/20250221-1509exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_0_reserves/output/20250305-2102exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_3_reserves/output/20250305-1514exp-export_mps"
    # output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_3_reserves++/output/20250307-1529exp-export_mps"
    output_path = "C:/Users/sonvicoleo/Documents/Test_RTE/BP23_4_reserves/output/20250310-1400exp-export_mps"


    
    cost_step1 = []
    cost_step2 = []
    cost_total_step2 = []
    temps_lecture_mps = []
    temps_conversion_fast = []
    temps_load_bases = []
    temps_opti1 = []
    temps_get_bases = []
    temps_lecture_resultat = []
    temps_creation_ensemble_semaine = []
    temps_heuristique_arrondi = []
    temps_heuristique_dmin = []
    temps_changement_borne = []
    temps_opti2 = []
    temps_total = []
    heure_defaillance_prod = []
    heure_defaillance_fcr_up = []
    heure_defaillance_fcr_down = []
    heure_defaillance_afrr_up = []
    heure_defaillance_affr_down = []
    heure_defaillance_mfrr_up = []
    heure_defaillance_mfrr_down = []
    heure_defaillance_rr_up = []
    heure_defaillance_rr_down = []
    quantite_defaillance_prod = []
    quantite_defaillance_fcr_up = []
    quantite_defaillance_fcr_down = []
    quantite_defaillance_afrr_up = []
    quantite_defaillance_affr_down = []
    quantite_defaillance_mfrr_up = []
    quantite_defaillance_mfrr_down = []
    quantite_defaillance_rr_up = []
    quantite_defaillance_rr_down = []
    bases = None

    ensemble_valeur_annuel = lecture_donnees_fast(study_path)

    temps_initial = time.perf_counter()
    for week in range(52):
        (costs,temps,heure_defaillance,quantite_defaillance,bases) = BP_week_fast_simple(output_path,ensemble_valeur_annuel,week,bases)
        temps_actuel = time.perf_counter() 
        temps_total.append(temps_actuel - temps_initial)
        temps_lecture_mps.append(temps[0])
        temps_conversion_fast.append(temps[1])
        temps_load_bases.append(temps[2])
        temps_opti1.append(temps[3])
        temps_get_bases.append(temps[4])
        temps_lecture_resultat.append(temps[5])
        temps_creation_ensemble_semaine.append(temps[6])
        temps_heuristique_arrondi.append(temps[7])
        temps_heuristique_dmin.append(temps[8])
        temps_changement_borne.append(temps[9])
        temps_opti2.append(temps[10])
        temps_initial = temps_actuel
        cost_step1.append(costs[0])
        cost_step2.append(costs[1])
        cost_total_step2.append(costs[1]+costs[2])
        heure_defaillance_prod.append(heure_defaillance[0])
        heure_defaillance_fcr_up.append(heure_defaillance[1])
        heure_defaillance_fcr_down.append(heure_defaillance[2])
        heure_defaillance_afrr_up.append(heure_defaillance[3])
        heure_defaillance_affr_down.append(heure_defaillance[4])
        heure_defaillance_mfrr_up.append(heure_defaillance[5])
        heure_defaillance_mfrr_down.append(heure_defaillance[6])
        heure_defaillance_rr_up.append(heure_defaillance[7])
        heure_defaillance_rr_down.append(heure_defaillance[8])
        quantite_defaillance_prod.append(quantite_defaillance[0])
        quantite_defaillance_fcr_up.append(quantite_defaillance[1])
        quantite_defaillance_fcr_down.append(quantite_defaillance[2])
        quantite_defaillance_afrr_up.append(quantite_defaillance[3])
        quantite_defaillance_affr_down.append(quantite_defaillance[4])
        quantite_defaillance_mfrr_up.append(quantite_defaillance[5])
        quantite_defaillance_mfrr_down.append(quantite_defaillance[6])
        quantite_defaillance_rr_up.append(quantite_defaillance[7])
        quantite_defaillance_rr_down.append(quantite_defaillance[8])

    de_BP_year = pd.DataFrame(data = {
        "Optim_1":cost_step1,"Optim_2":cost_step2,"post-traitement":cost_total_step2,
        "temps_total":temps_total,
        "temps_lecture_mps": temps_lecture_mps,
        "temps_conversion_fast": temps_conversion_fast,
        "temps_load_bases":temps_load_bases,
        "temps_opti1": temps_opti1,
        "temps_get_bases":temps_get_bases,
        "temps_lecture_resultat": temps_lecture_resultat ,
        "temps_creation_ensemble_semaine": temps_creation_ensemble_semaine,
        "temps_heuristique_arrondi": temps_heuristique_arrondi,
        "temps_heuristique_dmin": temps_heuristique_dmin,
        "temps_changement_borne": temps_changement_borne,
        "temps_opti2": temps_opti2,
        "heure_defaillance_prod": heure_defaillance_prod,
        "heure_defaillance_fcr_up":  heure_defaillance_fcr_up,
        "heure_defaillance_fcr_down": heure_defaillance_fcr_down ,
        "heure_defaillance_afrr_up": heure_defaillance_afrr_up ,
        "heure_defaillance_affr_down": heure_defaillance_affr_down ,
        "heure_defaillance_mfrr_up": heure_defaillance_mfrr_up,
        "heure_defaillance_mfrr_down": heure_defaillance_mfrr_down ,
        "heure_defaillance_rr_up":heure_defaillance_rr_up  ,
        "heure_defaillance_rr_down":heure_defaillance_rr_down  ,
        "quantite_defaillance_prod": quantite_defaillance_prod,
        "quantite_defaillance_fcr_up":  quantite_defaillance_fcr_up,
        "quantite_defaillance_fcr_down": quantite_defaillance_fcr_down ,
        "quantite_defaillance_afrr_up": quantite_defaillance_afrr_up ,
        "quantite_defaillance_affr_down": quantite_defaillance_affr_down ,
        "quantite_defaillance_mfrr_up": quantite_defaillance_mfrr_up,
        "quantite_defaillance_mfrr_down": quantite_defaillance_mfrr_down ,
        "quantite_defaillance_rr_up":quantite_defaillance_rr_up  ,
        "quantite_defaillance_rr_down":quantite_defaillance_rr_down  ,
        })
    de_BP_year.to_csv("result_year_fast_simple.csv",index=False)
