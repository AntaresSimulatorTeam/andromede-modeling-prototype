# Copyright (c) 2024, RTE (https://www.rte-france.com)
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
import logging
import os
import sys
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from configparser import ConfigParser
from pathlib import Path

from .converter import AntaresStudyConverter
from .logger import Logger

DEFAULT: dict = {}
LOGGER_PATH: str = os.path.join(os.path.dirname(__file__), "../data/logging.log")


class PathType:
    """file or directory path type for `argparse` parser

    The `PathType` class represents a type of argument that can be used
    with the `argparse` library.
    This class takes three boolean arguments, `exists`, `file_ok`, and `dir_ok`,
    which specify whether the path argument must exist, whether it can be a file,
    and whether it can be a directory, respectively.

    Example Usage::

        import argparse
        from antarest.main import PathType

        parser = argparse.ArgumentParser()
        parser.add_argument("--input", type=PathType(file_ok=True, exists=True))
        args = parser.parse_args()

        print(args.input)

    In the above example, `PathType` is used to specify the type of the `--input`
    argument for the `argparse` parser. The argument must be an existing file path.
    If the given path is not an existing file, the argparse library raises an error.
    The Path object representing the given path is then printed to the console.
    """

    def __init__(
        self,
        exists: bool = False,
        file_ok: bool = False,
        dir_ok: bool = False,
    ) -> None:
        if not (file_ok or dir_ok):
            msg = "Either `file_ok` or `dir_ok` must be set at a minimum."
            raise ValueError(msg)
        self.exists = exists
        self.file_ok = file_ok
        self.dir_ok = dir_ok

    def __call__(self, string: str) -> Path:
        """
        Check whether the given string represents a valid path.

        If `exists` is `False`, the method simply returns the given path.
        If `exists` is True, it checks whether the path exists and whether it is
        a file or a directory, depending on the values of `file_ok` and `dir_ok`.
        If the path exists and is of the correct type, the method returns the path;
        otherwise, it raises an :class:`argparse.ArgumentTypeError` with an
        appropriate error message.

        Args:
            string: file or directory path

        Returns:
            the file or directory path

        Raises
            argparse.ArgumentTypeError: if the path is invalid
        """
        file_path = Path(string).expanduser()
        if not self.exists:
            return file_path
        if self.file_ok and self.dir_ok:
            if file_path.exists():
                return file_path
            msg = f"The file or directory path does not exist: '{file_path}'"
            raise ArgumentTypeError(msg)
        elif self.file_ok:
            if file_path.is_file():
                return file_path
            elif file_path.exists():
                msg = f"The path is not a regular file: '{file_path}'"
            else:
                msg = f"The file path does not exist: '{file_path}'"
            raise ArgumentTypeError(msg)
        elif self.dir_ok:
            if file_path.is_dir():
                return file_path
            elif file_path.exists():
                msg = f"The path is not a directory: '{file_path}'"
            else:
                msg = f"The directory path does not exist: '{file_path}'"
            raise ArgumentTypeError(msg)
        else:  # pragma: no cover
            raise NotImplementedError((self.file_ok, self.dir_ok))


def parse_commandline() -> Namespace:
    """Parse command-line arguments using argparse to specify configuration file paths,
    logging options, and version display. Returns the parsed arguments."""
    parser = ArgumentParser()
    parser.add_argument(
        "-c",
        "--conf",
        type=PathType(exists=True, file_ok=True),
        help="Give the path of the configuration file",
        default="../data/config.ini",
    )
    parser.add_argument(
        "-l",
        "--logging",
        type=PathType(exists=True, file_ok=True),
        help="Give the path of the logger file",
        default=LOGGER_PATH,
    )
    parser.add_argument(
        "-i",
        "--study_path",
        type=PathType(exists=True, dir_ok=True),
        help="Give the path of the study_path",
    )
    parser.add_argument(
        "-o",
        "--output_path",
        type=PathType(exists=True, dir_ok=True),
        help="Give the path of the output path",
    )
    return parser.parse_args()


if __name__ == "__main__":
    config: dict = {}
    args = parse_commandline()
    logger: logging.Logger = Logger(__name__, args.logging)
    config_parser = ConfigParser()

    # Load the default configuration dictionary into the config parser.
    config_parser.read_dict(DEFAULT)

    if args.conf:
        # Check if the specified config file exists, if not, exit with an error message.
        if not os.path.exists(args.conf):
            sys.exit(f"Aborting: missing config file at {args.conf}")
        else:
            config_parser.read(args.conf)

    if not config_parser.has_section("study"):
        config_parser.add_section("study")

    if args.study_path:
        config_parser.set("study", "study_path", str(args.study_path))
    if args.output_path:
        config_parser.set("study", "output_path", str(args.output_path))

    converter = AntaresStudyConverter(
        Path(config_parser["study"].get("study_path")), logger=logger
    )
    converter.process_all()
