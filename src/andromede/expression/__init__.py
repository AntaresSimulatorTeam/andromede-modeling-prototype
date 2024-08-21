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

from .copy import CopyVisitor, copy_expression
from .degree import ExpressionDegreeVisitor, compute_degree
from .evaluate_parameters_efficient import ValueProvider
from .expression_efficient import (
    AdditionNode,
    ComparisonNode,
    ComponentParameterNode,
    DivisionNode,
    ExpressionNodeEfficient,
    ExpressionRange,
    InstancesTimeIndex,
    LiteralNode,
    MultiplicationNode,
    NegationNode,
    ParameterNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ScenarioOperatorName,
    ScenarioOperatorNode,
    SubstractionNode,
    TimeAggregatorName,
    TimeAggregatorNode,
    TimeOperatorName,
    TimeOperatorNode,
)
from .print import PrinterVisitor, print_expr
from .visitor import ExpressionVisitor, visit
