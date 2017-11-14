# coding=utf-8
"""Helpers for working with python ASTs."""
# Copyright 2017 Google LLC
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     https://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import ast
import collections
import itertools


def find_starargs(call_node):
  """Finds the index of starargs in a call's arguments, if present.

  NB: It is legal for *args to appear anywhere between the last positional
  argument and **kwargs.

  Arguments:
    call_node: (ast.Call) Call node to search.
  Returns:
    The index of the starargs argument, or -1 if not present.
  """
  if not call_node.starargs:
    return -1

  loc = lambda node: (node.lineno, node.col_offset)
  starargs_loc = loc(call_node.starargs)
  kwvalues = (kw.value for kw in call_node.keywords)
  locs = (loc(n) for n in itertools.chain(kwvalues, (call_node.starargs,)))
  return len(call_node.args) + sorted(locs).index(starargs_loc)


_AST_OP_NODES = (
    ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.Mod, ast.Pow, ast.LShift, ast.RShift, ast.BitAnd, ast.BitOr, ast.BitXor,
    ast.FloorDiv, ast.Invert, ast.Not, ast.UAdd, ast.USub
) 


class _TreeNormalizer(ast.NodeTransformer):
  """Replaces all op nodes with unique instances."""

  def visit(self, node):
    if isinstance(node, _AST_OP_NODES):
      return node.__class__()
    return super(_TreeNormalizer, self).visit(node)


def normalize(tree):
  _TreeNormalizer().visit(tree)
  return tree


def parse(src):
  return normalize(ast.parse(src))


def space_between(from_loc, to_loc, line, lines):
  """Builds a string with all the non-code characters between two locations.

  Arguments:
    from_loc: (int, int) Row, col position to start reading from.
    to_loc: (int, int) Row, col position to read until.
    line: (string) The line of the row in from_loc.
    lines: (list of string) All lines in the source, where lines[i] is the i-th
      line in the source code.
  """
  # TODO "line" parameter here is redundant
  if from_loc[0] == to_loc[0]:
    return line[from_loc[1]:to_loc[1]]

  result = lines[from_loc[0] - 1][from_loc[1]:]
  for line in lines[from_loc[0]:to_loc[0] - 1]:
    result += line
  else:
    line = to_loc
  if to_loc[1]:
    result += lines[to_loc[0] - 1][:to_loc[1]]
  return result


def setup_props(node):
  if not hasattr(node, 'a'):
    try:
      node.a = collections.defaultdict(lambda: '')
    except AttributeError:
      pass


def prop(node, name):
  if hasattr(node, 'a'):
    return node.a[name]
  return None


def setprop(node, name, value):
  setup_props(node)
  node.a[name] = value


def appendprop(node, name, value):
  node.a[name] += value


def prependprop(node, name, value):
  node.a[name] = value + node.a[name]


def find_nodes_by_type(node, accept_types):
  visitor = FindNodeVisitor(lambda n: isinstance(n, accept_types))
  visitor.visit(node)
  return visitor.results


class FindNodeVisitor(ast.NodeVisitor):

  def __init__(self, condition):
    self._condition = condition
    self.results = []

  def visit(self, node):
    if self._condition(node):
      self.results.append(node)
    super(FindNodeVisitor, self).visit(node)
