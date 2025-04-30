from pathlib import Path

import pypsa
import pytest


@pytest.mark.parametrize(
    "state_of_charge_initial, standing_loss, cyclic",
    [
        (100.0, 0.0, True),
        (0.0, 0.1, True),
        (100.0, 0.1, True),
        (100.0, 0.0, False),
    ],
)
def test_storage_unit(
    systems_dir: Path,
    series_dir: Path,
    state_of_charge_initial: float,
    standing_loss: float,
    cyclic: bool,
) -> None:
    # Building the PyPSA test problem with a storage unit
    T = 10

    n1 = pypsa.Network(name="Demo3", snapshots=[i for i in range(T)])
    n1.add("Bus", "pypsatown", v_nom=1)
    n1.add(
        "Load", "pypsaload", bus="pypsatown", p_set=[i * 20 for i in range(T)], q_set=0
    )
    n1.add(
        "Generator",
        "pypsagenerator",
        bus="pypsatown",
        p_nom_extendable=False,
        marginal_cost=50,  # €/MWh
        p_nom=150.0,  # MW
    )
    n1.add(
        "StorageUnit",
        "pypsastorage",
        bus="pypsatown",
        p_nom=100,  # MW
        max_hours=10,  # Hours of storage at full output
        efficiency_store=0.9,
        efficiency_dispatch=0.85,
        standing_loss=standing_loss,
        state_of_charge_initial=state_of_charge_initial,
        marginal_cost=50.0,  # €/MWh
        p_min_pu=-1,
        p_max_pu=1,
        cyclic_state_of_charge=cyclic,
        cyclic_state_of_charge_per_period=cyclic,
    )
    n1.optimize()
    print(n1.storage_units_t["state_of_charge"])
    print(n1.storage_units_t["p"])
