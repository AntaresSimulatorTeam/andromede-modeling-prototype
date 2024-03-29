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

"""
Specific modelling for "instantiated" linear expressions,
with only variables and literal coefficients.
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, TypeVar, Union

from andromede.expression.indexing_structure import IndexingStructure
from andromede.expression.scenario_operator import ScenarioOperator
from andromede.expression.time_operator import TimeAggregator, TimeOperator
from andromede.model.model import PortFieldId

T = TypeVar("T")

EPS = 10 ** (-16)


def is_close_abs(value: float, other_value: float, eps: float) -> bool:
    return abs(value - other_value) < eps


def is_zero(value: float) -> bool:
    return is_close_abs(value, 0, EPS)


def is_one(value: float) -> bool:
    return is_close_abs(value, 1, EPS)


def is_minus_one(value: float) -> bool:
    return is_close_abs(value, -1, EPS)


@dataclass(frozen=True)
class TermKey:

    """
    Utility class to provide key for a term that contains all term information except coefficient
    """

    component_id: str
    variable_name: str
    time_operator: Optional[TimeOperator]
    time_aggregator: Optional[TimeAggregator]
    scenario_operator: Optional[ScenarioOperator]


@dataclass(frozen=True)
class Term:
    """
    One term in a linear expression: for example the "10x" par in "10x + 5y + 5"

    Args:
        coefficient: the coefficient for that term, for example "10" in "10x"
        variable_name: the name of the variable, for example "x" in "10x"
    """

    coefficient: float
    component_id: str
    variable_name: str
    structure: IndexingStructure = field(
        default=IndexingStructure(time=True, scenario=True)
    )
    time_operator: Optional[TimeOperator] = None
    time_aggregator: Optional[TimeAggregator] = None
    scenario_operator: Optional[ScenarioOperator] = None

    # TODO: It may be useful to define __add__, __sub__, etc on terms, which should return a linear expression ?

    def is_zero(self) -> bool:
        return is_zero(self.coefficient)

    def str_for_coeff(self) -> str:
        str_for_coeff = ""
        if is_one(self.coefficient):
            str_for_coeff = "+"
        elif is_minus_one(self.coefficient):
            str_for_coeff = "-"
        else:
            str_for_coeff = "{:+g}".format(self.coefficient)
        return str_for_coeff

    def __str__(self) -> str:
        # Useful for debugging tests
        result = self.str_for_coeff() + str(self.variable_name)
        if self.time_operator is not None:
            result += f".{str(self.time_operator)}"
        if self.time_aggregator is not None:
            result += f".{str(self.time_aggregator)}"
        if self.scenario_operator is not None:
            result += f".{str(self.scenario_operator)}"
        return result

    def number_of_instances(self) -> int:
        if self.time_aggregator is not None:
            return self.time_aggregator.size()
        else:
            if self.time_operator is not None:
                return self.time_operator.size()
            else:
                return 1


def generate_key(term: Term) -> TermKey:
    return TermKey(
        term.component_id,
        term.variable_name,
        term.time_operator,
        term.time_aggregator,
        term.scenario_operator,
    )


def _merge_dicts(
    lhs: Dict[TermKey, Term],
    rhs: Dict[TermKey, Term],
    merge_func: Callable[[Term, Term], Term],
    neutral: float,
) -> Dict[TermKey, Term]:
    res = {}
    for k, v in lhs.items():
        res[k] = merge_func(
            v,
            rhs.get(
                k,
                Term(
                    neutral,
                    v.component_id,
                    v.variable_name,
                    v.structure,
                    v.time_operator,
                    v.time_aggregator,
                    v.scenario_operator,
                ),
            ),
        )
    for k, v in rhs.items():
        if k not in lhs:
            res[k] = merge_func(
                Term(
                    neutral,
                    v.component_id,
                    v.variable_name,
                    v.structure,
                    v.time_operator,
                    v.time_aggregator,
                    v.scenario_operator,
                ),
                v,
            )
    return res


def _merge_is_possible(lhs: Term, rhs: Term) -> None:
    if lhs.component_id != rhs.component_id or lhs.variable_name != rhs.variable_name:
        raise ValueError("Cannot merge terms for different variables")
    if (
        lhs.time_operator != rhs.time_operator
        or lhs.time_aggregator != rhs.time_aggregator
        or lhs.scenario_operator != rhs.scenario_operator
    ):
        raise ValueError("Cannot merge terms with different operators")
    if lhs.structure != rhs.structure:
        raise ValueError("Cannot merge terms with different structures")


def _add_terms(lhs: Term, rhs: Term) -> Term:
    _merge_is_possible(lhs, rhs)
    return Term(
        lhs.coefficient + rhs.coefficient,
        lhs.component_id,
        lhs.variable_name,
        lhs.structure,
        lhs.time_operator,
        lhs.time_aggregator,
        lhs.scenario_operator,
    )


def _substract_terms(lhs: Term, rhs: Term) -> Term:
    _merge_is_possible(lhs, rhs)
    return Term(
        lhs.coefficient - rhs.coefficient,
        lhs.component_id,
        lhs.variable_name,
        lhs.structure,
        lhs.time_operator,
        lhs.time_aggregator,
        lhs.scenario_operator,
    )


class LinearExpression:
    """
    Represents a linear expression with respect to variable names, for example 10x + 5y + 2.

    Operators may be used for construction.

    Args:
        terms: the list of variable terms, for example 10x and 5y in "10x + 5y + 2".
        constant: the constant term, for example 2 in "10x + 5y + 2"

    Examples:
        Operators may be used for construction:

        >>> LinearExpression([], 10) + LinearExpression([Term(10, "x")], 0)
        LinearExpression([Term(10, "x")], 10)
    """

    terms: Dict[TermKey, Term]
    constant: float

    def __init__(
        self,
        terms: Optional[Union[Dict[TermKey, Term], List[Term]]] = None,
        constant: Optional[float] = None,
    ) -> None:
        self.constant = 0
        self.terms = {}

        if constant is not None:
            # += b
            self.constant = constant
        if terms is not None:
            # Allows to give two different syntax in the constructor:
            #   - List[Term] is natural
            #   - Dict[str, Term] is useful when constructing a linear expression from the terms of another expression
            if isinstance(terms, dict):
                for term_key, term in terms.items():
                    if not term.is_zero():
                        self.terms[term_key] = term
            elif isinstance(terms, list):
                for term in terms:
                    if not term.is_zero():
                        self.terms[generate_key(term)] = term
            else:
                raise TypeError(
                    f"Terms must be either of type Dict[str, Term] or List[Term], whereas {terms} is of type {type(terms)}"
                )

    def is_zero(self) -> bool:
        return len(self.terms) == 0 and is_zero(self.constant)

    def str_for_constant(self) -> str:
        if is_zero(self.constant):
            return ""
        else:
            return "{:+g}".format(self.constant)

    def __str__(self) -> str:
        # Useful for debugging tests
        result = ""
        if self.is_zero():
            result += "0"
        else:
            for term in self.terms.values():
                result += str(term)

            result += self.str_for_constant()

        return result

    def __eq__(self, rhs: object) -> bool:
        return (
            isinstance(rhs, LinearExpression)
            and is_close_abs(self.constant, rhs.constant, EPS)
            and self.terms
            == rhs.terms  # /!\ There may be float equality comparison in the terms values
        )

    def __iadd__(self, rhs: "LinearExpression") -> "LinearExpression":
        if not isinstance(rhs, LinearExpression):
            return NotImplemented
        self.constant += rhs.constant
        aggregated_terms = _merge_dicts(self.terms, rhs.terms, _add_terms, 0)
        self.terms = aggregated_terms
        self.remove_zeros_from_terms()
        return self

    def __add__(self, rhs: "LinearExpression") -> "LinearExpression":
        result = LinearExpression()
        result += self
        result += rhs
        return result

    def __isub__(self, rhs: "LinearExpression") -> "LinearExpression":
        if not isinstance(rhs, LinearExpression):
            return NotImplemented
        self.constant -= rhs.constant
        aggregated_terms = _merge_dicts(self.terms, rhs.terms, _substract_terms, 0)
        self.terms = aggregated_terms
        self.remove_zeros_from_terms()
        return self

    def __sub__(self, rhs: "LinearExpression") -> "LinearExpression":
        result = LinearExpression()
        result += self
        result -= rhs
        return result

    def __neg__(self) -> "LinearExpression":
        result = LinearExpression()
        result -= self
        return result

    def __imul__(self, rhs: "LinearExpression") -> "LinearExpression":
        if not isinstance(rhs, LinearExpression):
            return NotImplemented

        if self.terms and rhs.terms:
            raise ValueError("Cannot multiply two non constant expression")
        else:
            if self.terms:
                left_expr = self
                const_expr = rhs
            else:
                # It is possible that both expr are constant
                left_expr = rhs
                const_expr = self
            if is_close_abs(const_expr.constant, 0, EPS):
                return LinearExpression()
            elif is_close_abs(const_expr.constant, 1, EPS):
                _copy_expression(left_expr, self)
            else:
                left_expr.constant *= const_expr.constant
                for term_key, term in left_expr.terms.items():
                    left_expr.terms[term_key] = Term(
                        term.coefficient * const_expr.constant,
                        term.component_id,
                        term.variable_name,
                        term.structure,
                        term.time_operator,
                        term.time_aggregator,
                        term.scenario_operator,
                    )
                _copy_expression(left_expr, self)
        return self

    def __mul__(self, rhs: "LinearExpression") -> "LinearExpression":
        result = LinearExpression()
        result += self
        result *= rhs
        return result

    def __itruediv__(self, rhs: "LinearExpression") -> "LinearExpression":
        if not isinstance(rhs, LinearExpression):
            return NotImplemented

        if rhs.terms:
            raise ValueError("Cannot divide by a non constant expression")
        else:
            if is_close_abs(rhs.constant, 0, EPS):
                raise ZeroDivisionError("Cannot divide expression by zero")
            elif is_close_abs(rhs.constant, 1, EPS):
                return self
            else:
                self.constant /= rhs.constant
                for term_key, term in self.terms.items():
                    self.terms[term_key] = Term(
                        term.coefficient / rhs.constant,
                        term.component_id,
                        term.variable_name,
                        term.structure,
                        term.time_operator,
                        term.time_aggregator,
                        term.scenario_operator,
                    )
        return self

    def __truediv__(self, rhs: "LinearExpression") -> "LinearExpression":
        result = LinearExpression()
        result += self
        result /= rhs

        return result

    def remove_zeros_from_terms(self) -> None:
        # TODO: Not optimized, checks could be done directly when doing operations on self.linear_term to avoid copies
        for term_key, term in self.terms.copy().items():
            if is_close_abs(term.coefficient, 0, EPS):
                del self.terms[term_key]

    def is_valid(self) -> bool:
        nb_instances = None
        for term in self.terms.values():
            term_instances = term.number_of_instances()
            if nb_instances is None:
                nb_instances = term_instances
            else:
                if term_instances != nb_instances:
                    raise ValueError(
                        "The terms of the linear expression {self} do not have the same number of instances"
                    )
        return True

    def number_of_instances(self) -> int:
        if self.is_valid():
            # All terms have the same number of instances, just pick one
            return self.terms[next(iter(self.terms))].number_of_instances()
        else:
            raise ValueError(f"{self} is not a valid linear expression")


def _copy_expression(src: LinearExpression, dst: LinearExpression) -> None:
    dst.terms = src.terms
    dst.constant = src.constant
