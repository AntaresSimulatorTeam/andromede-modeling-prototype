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

from andromede.expression import ExpressionNode, PrinterVisitor, param, var, visit


def test_comparison() -> None:
    x = var("x")
    p = param("p")
    expr: ExpressionNode = (5 * x + 3) >= p - 2

    assert visit(expr, PrinterVisitor()) == "((5.0 * x) + 3.0) >= (p - 2.0)"
