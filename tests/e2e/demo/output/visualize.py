# Copyright (c) 2025, RTE (https://www.rte-france.com)
#
# See AUTHORS.txt
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0
#
# This file is part of the Antares project.

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes


def read_output(filename: str) -> pd.DataFrame:
    output_data = pd.read_csv(filename, sep=";", index_col=0)
    return output_data.dropna(axis=1)


def _set_axes_params() -> None:
    custom_colors = plt.cm.tab20.colors
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=custom_colors)
    plt.rcParams.update({"font.size": 18})


def _beautify(ax: Axes) -> None:
    ax.set_xlabel("Hour")
    ax.set_ylabel("MW")
    ax.set_xlim(1, 24)
    ax.legend(ncol=2, bbox_to_anchor=(0, 1), loc="lower left")


def plot_generation_stack(generation_data: pd.DataFrame, ax: Axes) -> None:
    ax.stackplot(
        generation_data.index, generation_data.T, labels=generation_data.columns
    )


def plot_battery_soc(filename: pd.DataFrame) -> None:
    data = pd.read_csv(filename, sep=";", index_col=0)[["battery_SOC"]]
    _, ax = plt.subplots(figsize=(12, 4))
    ax.plot(data.index, data["battery_SOC"], label="battery_SOC")
    ax.legend()
    ax.set_xlabel("Hour")
    ax.set_ylabel("MWh")


def plot_load(load_data: pd.DataFrame, ax: Axes) -> None:
    ax.plot(load_data.index, load_data["load"], color="black")


def visualize(filename: str) -> None:
    _set_axes_params()
    output_data = read_output(filename)
    generation_data = output_data.drop(columns=["load"])
    _, ax = plt.subplots(figsize=(12, 6))
    plot_generation_stack(
        generation_data.drop(columns=["DE_spillage", "Battery1_p_injection"]), ax
    )
    plot_generation_stack(generation_data[["DE_spillage", "Battery1_p_injection"]], ax)
    plot_load(output_data[["load"]], ax)
    _beautify(ax)
