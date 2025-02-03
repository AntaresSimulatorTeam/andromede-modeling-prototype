from tests.test_BP_week import (BP_week,lecture_donnees)
import time
import pandas as pd
from tests.generate_mps_files import *

def test_BP_year():

    study_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_france_year"
    antares_path = "D:/AppliRTE/bin/antares-solver.exe"
    # output_path = generate_mps_file(study_path,antares_path)
    # output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_mfrr_FR_1_week/output/20250130-0937exp-export_mps"
    output_path = "C:/Users/sonvicoleo/Documents/Test_finaux/BP23_france_year/output/20250131-0943exp-export_mps"

    cost_step1 = []
    cost_step2 = []
    week_cost = []
    temps= []

    (ensemble_valeur_annuel,ensemble_dmins_etranger) = lecture_donnees(study_path)

    temps_initial = time.perf_counter()
    for week in range(1):
        costs = BP_week(study_path,output_path,ensemble_valeur_annuel,ensemble_dmins_etranger,week)
        temps_actuel = time.perf_counter() 
        temps.append(temps_actuel - temps_initial)
        temps_initial = temps_actuel
        week_cost.append(costs)
        cost_step1.append(costs[0])
        cost_step2.append(costs[1])


    de_BP_year = pd.DataFrame(data = {
        "Optim_1":cost_step1,"Optim_2":cost_step2,
        "Temps":temps})
    de_BP_year.to_csv("result_year.csv",index=False)







