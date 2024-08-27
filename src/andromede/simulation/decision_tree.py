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

import math
from dataclasses import dataclass, field
from typing import Dict, Generator, Iterable, List, Optional, Set

from anytree import LevelOrderIter, NodeMixin

from andromede.expression import (
    Comparator,
    ComparisonNode,
    ExpressionNode,
    literal,
    visit,
)
from andromede.expression.attributes import (
    VariableGetterVisitor,
    VariableNamePrependerVisitor,
)
from andromede.expression.indexing_structure import IndexingStructure
from andromede.model.common import ProblemContext
from andromede.model.constraint import Constraint
from andromede.model.model import model
from andromede.model.variable import Variable, float_variable
from andromede.simulation.time_block import TimeBlock
from andromede.study.network import Component, Network, create_component


@dataclass(frozen=True)
class InterDecisionTimeScenarioConfig:
    blocks: List[TimeBlock]
    scenarios: int


@dataclass
class CouplingInfo:
    variables: Set[str] = field(default_factory=set)
    constraints: Dict[str, ExpressionNode] = field(default_factory=dict)


class DecisionTreeNode(NodeMixin):
    id: str
    config: InterDecisionTimeScenarioConfig
    network: Network
    prob: float

    coupling_network: Network
    coupling_info: CouplingInfo

    def __init__(
        self,
        id: str,
        config: InterDecisionTimeScenarioConfig,
        network: Network,
        parent: Optional["DecisionTreeNode"] = None,
        children: Optional[Iterable["DecisionTreeNode"]] = None,
        prob: float = 1.0,
        coupling_network: Network = Network("_Coupler"),
        coupling_info: CouplingInfo = CouplingInfo(),
    ) -> None:
        self.id = id
        self.config = config
        self.network = network
        self.coupling_network = coupling_network
        self.coupling_info = coupling_info
        self.parent = parent

        if prob < 0 or 1 < prob:
            raise ValueError("Probability must be a value in the range [0, 1]")

        self.prob = prob * (parent.prob if parent is not None else 1)
        if children:
            self.children = children

    def traverse(
        self, depth: Optional[int] = None
    ) -> Generator["DecisionTreeNode", None, None]:
        yield from LevelOrderIter(self, maxlevel=depth)

    def is_leaves_prob_sum_one(self) -> bool:
        if not self.children:
            return True

        # Since we multiply the child's prob by the parent's prob
        # in the constructor, the sum of the children prob should
        # equal 1 * parent.prob if the values were set correctly
        if not math.isclose(self.prob, sum(child.prob for child in self.children)):
            return False

        # Recursively check if child nodes have their children's
        # probability sum equal to one
        return all(child.is_leaves_prob_sum_one() for child in self.children)

    def connect_from_parent(
        self, component_par: Component, component_chd: Component, expr: ExpressionNode
    ) -> None:
        if self.parent and (component_par not in self.parent.network.all_components):
            raise RuntimeError(
                f"Component {component_par.id} not present in parent's network!"
            )

        if component_chd not in self.network.all_components:
            raise RuntimeError(
                f"Component {component_chd.id} not present in child's network!"
            )

        if not isinstance(expr, ComparisonNode):
            raise ValueError(
                f"Expression must be a comparison node (lhs for parent, rhs for child)."
            )

        expr_par = expr.left
        expr_chd = expr.right

        prefix_par = f"{self.parent.id}_{component_par.id}" if self.parent else ""
        prefix_chd = f"{self.id}_{component_chd.id}"

        for var in visit(expr_par, VariableGetterVisitor()):
            if not component_par.is_variable_in_model(var):
                raise ValueError(
                    f"Variable {var} not present in parent's {component_par.id}"
                )

            self.coupling_info.variables.add(f"{prefix_par}_{var}")

        for var in visit(expr_chd, VariableGetterVisitor()):
            if not component_chd.is_variable_in_model(var):
                raise ValueError(
                    f"Variable {var} not present in child's {component_chd.id}"
                )

            self.coupling_info.variables.add(f"{prefix_chd}_{var}")

        new_expr_par = visit(expr_par, VariableNamePrependerVisitor(prefix_par))
        new_expr_chd = visit(expr_chd, VariableNamePrependerVisitor(prefix_chd))

        if expr.comparator == Comparator.EQUAL:
            new_expr = new_expr_par == new_expr_chd
        elif expr.comparator == Comparator.LESS_THAN:
            new_expr = new_expr_par <= new_expr_chd
        else:
            new_expr = new_expr_par >= new_expr_chd

        self.coupling_info.constraints[
            f"{prefix_par}_{prefix_chd}_{len(self.coupling_info.constraints)}"
        ] = new_expr

    def connect_to_children(
        self, component_par: Component, component_chd: Component, expr: ExpressionNode
    ) -> None:
        if not self.children:
            raise RuntimeError("Cannot connect downwards because no child is defined!")

        for child in self.children:
            child.connect_from_parent(component_par, component_chd, expr)

    def _add_coupling_component(self) -> None:
        variables: List[Variable] = []
        constraints: List[Constraint] = []

        """
        Here and below, we use (and mostly abuse!) of the fact that
        both coupling_network and coupling_info attributes are initialized,
        or bound, at the function definition since they are default arguments!
        It allows us to not iterate over the tree, since all nodes share the same
        coupling_network and coupling_info objects.

        However, IT IS BAD DESIGN!
        But for now it will suffice since the inner workings will change once
        Thomas has changed the AST instantiation
        TODO Update this once the new AST is merged
        """
        for var_name in self.coupling_info.variables:
            variables.append(
                # TODO For now, unbounded positive float variable
                float_variable(
                    var_name,
                    lower_bound=literal(0),
                    structure=IndexingStructure(False, False),
                    context=ProblemContext.INVESTMENT,
                ),
            )

        for cst_name, expr in self.coupling_info.constraints.items():
            constraints.append(
                Constraint(
                    name=cst_name,
                    expression=expr,
                    context=ProblemContext.INVESTMENT,
                ),
            )

        self.coupling_network.add_component(
            create_component(
                model(
                    id="",
                    variables=variables,
                    constraints=constraints,
                ),
                id="coupling",
            )
        )
