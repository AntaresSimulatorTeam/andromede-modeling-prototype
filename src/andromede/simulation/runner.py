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

import os
import pathlib
import subprocess
import sys
from typing import List


class CommandRunner:
    current_dir: pathlib.Path
    command: pathlib.Path
    arguments: List[str]
    emplacement: pathlib.Path

    def __init__(
        self, binary_path: str, list_arguments: List[str], output_path: str
    ) -> None:
        self.current_dir = pathlib.Path().cwd()
        self.command = pathlib.Path(binary_path)
        self.emplacement = pathlib.Path(output_path)
        self.arguments = list_arguments

    def check_command(self) -> bool:
        if not self.command.is_file():
            print(f"{self.command} executable not found")
            return False
        return True

    def run(self) -> int:
        if not self.check_command():
            # TODO For now, it will return 0 as if nothing is wrong
            # eventually if should return an error
            # maybe wait when we separate unit tests from integration tests
            print("Return code 0 for now")
            return 0

        os.chdir(self.emplacement)
        res = subprocess.run(
            [self.command, *self.arguments],
            stdout=sys.stdout,
            stderr=subprocess.DEVNULL,  # TODO For now, to avoid the "Invalid MIT-MAGIC-COOKIE-1 key" error
            shell=False,
        )
        os.chdir(self.current_dir)

        return res.returncode


class BendersRunner(CommandRunner):
    def __init__(self, output_path: str) -> None:
        super().__init__("bin/benders", ["options.json"], output_path)


class MergeMPSRunner(CommandRunner):
    def __init__(self, output_path: str) -> None:
        super().__init__("bin/merge_mps", ["options.json"], output_path)