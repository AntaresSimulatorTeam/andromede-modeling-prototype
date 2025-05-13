"""
Script to convert a PyPSA study to Andromede format and run it.

This script loads a PyPSA study using the load_pypsa_study function,
converts it to Andromede format, and runs the converted study.
"""

import math
from pathlib import Path

from andromede.input_converter.src.logger import Logger
from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.pypsa_converter.pypsa_converter import PyPSAStudyConverter
from andromede.pypsa_converter.utils import transform_to_yaml
from andromede.simulation.optimization import OptimizationProblem, build_problem
from andromede.simulation.time_block import TimeBlock
from andromede.study.parsing import InputSystem, parse_yaml_components
from andromede.study.resolve_components import (
    System,
    build_data_base,
    build_network,
    resolve_system,
)


def load_pypsa_study():
    """
    Load a PyPSA study from a NetCDF file, preparing it for analysis or manipulation.

    This function loads a PyPSA network from a predefined NetCDF file located in the
    pypsa_input_files directory. It uses a relative path to avoid hardcoding the
    absolute path.

    Returns:
        pypsa.Network: A PyPSA network object loaded from the NetCDF file,
                      containing all components and settings from the dataset.
    """
    import os
    from pathlib import Path

    import pypsa

    # Get the directory of the current file
    current_dir = Path(__file__).parent

    # Define the relative path to the input file
    input_file = current_dir / "pypsa_input_files" / "base_s_6_elec_lvopt_.nc"

    # Load the PyPSA network from the file
    network = pypsa.Network(input_file)

    # Rename the loads and links to avoid duplicate names with corresponding buses
    network = rename_pypsa_loads(network)
    network = rename_pypsa_stores(network)

    return network


def rename_pypsa_loads(network):

    network.loads.index += " load"
    for key, val in network.loads_t.items():
        val.columns = val.columns + " load"

    return network


def rename_pypsa_stores(network):

    network.stores.index += " link"
    for key, val in network.stores_t.items():
        val.columns = val.columns + " link"

    return network


def replace_lines_by_links(network):
    """
    Replace lines in a PyPSA network with equivalent links.

    This function converts transmission lines to links, which allows for more
    flexible modeling of power flow constraints. Each line is replaced with
    two links (one for each direction) to maintain bidirectional flow capability.

    Args:
        network (pypsa.Network): The PyPSA network to modify

    Returns:
        pypsa.Network: The modified network with lines replaced by links
    """

    # Create a copy of the lines DataFrame to iterate over
    lines = network.lines.copy()

    # For each line, create two links (one for each direction)
    for idx, line in lines.iterrows():
        # Create a unique name for the links
        link_name_forward = f"{idx} link forward"
        link_name_backward = f"{idx} link backward"

        # Get line parameters
        bus0 = line["bus0"]
        bus1 = line["bus1"]
        s_nom = line["s_nom"]

        # Calculate efficiency based on line resistance and reactance
        if "r" in line and "x" in line and (line["r"] > 0 or line["x"] > 0):
            # Simple model: efficiency is reduced based on resistance
            r_pu = line["r"]
            efficiency = 1 / (1 + r_pu)
        else:
            # Default high efficiency if no resistance data
            efficiency = 0.98

        # Add forward link
        network.add(
            "Link",
            link_name_forward,
            bus0=bus0,
            bus1=bus1,
            p_nom=s_nom,  # Use line capacity as link capacity
            efficiency=efficiency,
        )

        # Add backward link
        network.add(
            "Link",
            link_name_backward,
            bus0=bus1,  # Reversed direction
            bus1=bus0,  # Reversed direction
            p_nom=s_nom,
            efficiency=efficiency,
        )

    # Remove the original lines
    network.lines = network.lines.drop(lines.index)

    # Clean up lines_t time series if they exist
    for key in list(network.lines_t.keys()):
        if not network.lines_t[key].empty:
            network.lines_t[key] = network.lines_t[key].drop(
                columns=lines.index, errors="ignore"
            )

    return network


def convert_pypsa_network(
    pypsa_network,
    systems_dir: Path,
    series_dir: Path,
) -> InputSystem:
    """
    Convert a PyPSA network to an Andromede InputSystem.

    Args:
        pypsa_network: The PyPSA network to convert
        systems_dir: Directory to store system files
        series_dir: Directory to store time series data

    Returns:
        InputSystem: The converted Andromede InputSystem
    """
    logger = Logger(__name__, Path(""))
    converter = PyPSAStudyConverter(pypsa_network, logger, systems_dir, series_dir)
    input_system_from_pypsa_converter = converter.to_andromede_study()

    return input_system_from_pypsa_converter


def build_problem_from_system(
    resolved_system: System, input_system: InputSystem, series_dir: Path, timesteps: int
) -> OptimizationProblem:
    """
    Build an optimization problem from a resolved system.

    Args:
        resolved_system: The resolved Andromede system
        input_system: The input system
        series_dir: Directory containing time series data
        timesteps: Number of timesteps in the simulation

    Returns:
        OptimizationProblem: The built optimization problem
    """
    database = build_data_base(input_system, Path(series_dir))
    network = build_network(resolved_system)
    problem = build_problem(
        network,
        database,
        TimeBlock(1, [i for i in range(timesteps)]),
        1,
    )

    return problem


def main():
    """
    Main function to convert a PyPSA study to Andromede format and run it.
    """
    # Set up logger
    logger = Logger(__name__, Path(""))

    # Define directories for systems and series
    current_dir = Path(__file__).parent
    systems_dir = current_dir / "systems"
    series_dir = current_dir / "series"

    # Create directories if they don't exist
    systems_dir.mkdir(exist_ok=True)
    series_dir.mkdir(exist_ok=True)

    # Load the PyPSA study
    logger.info("Loading PyPSA study...")
    pypsa_network = load_pypsa_study()
    logger.info(
        f"Loaded PyPSA network with {len(pypsa_network.buses)} buses and {len(pypsa_network.generators)} generators"
    )
    logger.info("Solving PyPSA network before line to link...")
    pypsa_network.optimize()
    logger.info(f"PyPSA objective value: {pypsa_network.objective}")
    logger.info("Replacing line by links")
    network = replace_lines_by_links(pypsa_network)

    # Get the number of timesteps
    T = len(pypsa_network.snapshots)
    logger.info(f"Number of timesteps: {T}")

    # Convert to Andromede System
    logger.info("Converting PyPSA network to Andromede format...")
    input_system_from_pypsa_converter = convert_pypsa_network(
        pypsa_network, systems_dir, series_dir
    )

    # Save the InputSystem to YAML
    system_filename = "pypsa_study.yml"
    logger.info(f"Saving Andromede system to {systems_dir / system_filename}...")
    transform_to_yaml(
        model=input_system_from_pypsa_converter,
        output_path=systems_dir / system_filename,
    )

    # Load the model library
    logger.info("Loading model library...")
    # Get the path to the project root by going up two levels from the current directory
    project_root = Path(__file__).parents[2]
    pypsa_models_path = (
        project_root / "src/andromede/libs/pypsa_models/pypsa_models.yml"
    )
    logger.info(f"Loading PyPSA models from {pypsa_models_path}...")
    with open(pypsa_models_path) as lib_file:
        input_libraries = [parse_yaml_library(lib_file)]
    result_lib = resolve_library(input_libraries)

    # Resolve the system
    logger.info("Resolving the system...")
    resolved_system = resolve_system(input_system_from_pypsa_converter, result_lib)

    # Build and solve the optimization problem
    logger.info("Building and solving the optimization problem...")
    problem = build_problem_from_system(
        resolved_system, input_system_from_pypsa_converter, series_dir, T
    )

    # Solve the problem
    status = problem.solver.Solve()

    # Log the results
    if status == problem.solver.OPTIMAL:
        logger.info("Optimization problem solved successfully!")
        logger.info(f"Objective value: {problem.solver.Objective().Value()}")
    else:
        logger.error(f"Failed to solve optimization problem. Status: {status}")

    # Optimize PyPSA network
    logger.info("Solving PyPSA network after line to link...")
    pypsa_network.optimize()
    logger.info(f"PyPSA objective value: {pypsa_network.objective}")


if __name__ == "__main__":
    main()
