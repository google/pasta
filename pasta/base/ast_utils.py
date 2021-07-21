# coding=utf-8
"""Helpers for working with python ASTs."""
# Copyright 2021 Google LLC
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
import sys
import re

import pasta
from pasta.augment import errors
from pasta.base import formatting as fmt

# From PEP-0263 -- https://www.python.org/dev/peps/pep-0263/
_CODING_PATTERN = re.compile('^[ \t\v]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)')


def _ast_op_nodes(astlib):
  return (astlib.And, astlib.Or, astlib.Eq, astlib.NotEq, astlib.Is,
          astlib.IsNot, astlib.In, astlib.NotIn, astlib.Lt, astlib.LtE,
          astlib.Gt, astlib.GtE, astlib.Add, astlib.Sub, astlib.Mult,
          astlib.Div, astlib.Mod, astlib.Pow, astlib.LShift, astlib.RShift,
          astlib.BitAnd, astlib.BitOr, astlib.BitXor, astlib.FloorDiv,
          astlib.Invert, astlib.Not, astlib.UAdd, astlib.USub)


def parse(src, astlib=ast):
  """Replaces ast.parse; ensures additional properties on the parsed tree.

  This enforces the assumption that each node in the ast is unique.
  """

  class _TreeNormalizer(astlib.NodeTransformer):
    """Replaces all op nodes with unique instances."""

    def visit(self, node):
      if isinstance(node, _ast_op_nodes(astlib)):
        return node.__class__()
      return super(_TreeNormalizer, self).visit(node)

  tree=astlib.parse(sanitize_source(src))
  _TreeNormalizer().visit(tree)
  return tree


def sanitize_source(src):
  """Strip the 'coding' directive from python source code, if present.

  This is a workaround for https://bugs.python.org/issue18960. Also see PEP-0263.
  """
  src_lines = src.splitlines(True)
  for i, line in enumerate(src_lines[:2]):
    if _CODING_PATTERN.match(line):
      src_lines[i] = re.sub('#.*$', '# (removed coding)', line)
  return ''.join(src_lines)


def find_nodes_by_type(node, accept_types, astlib=ast):
  visitor = get_find_node_visitor((lambda n: isinstance(n, accept_types)),
                                  astlib=astlib)
  visitor.visit(node)
  return visitor.results


def get_find_node_visitor(condition, astlib=ast):

  class FindNodeVisitor(astlib.NodeVisitor):

    def __init__(self, condition):
      self._condition = condition
      self.results = []

    def visit(self, node):
      if self._condition(node):
        self.results.append(node)
      super(FindNodeVisitor, self).visit(node)

  return FindNodeVisitor(condition)


def get_last_child(node, astlib=ast):
  """Get the last child node of a block statement.

  The input must be a block statement (e.g. ast.For, ast.With, etc).

  Examples:
    1. with first():
         second()
         last

    2. try:
         first()
       except:
         second()
       finally:
         last

  In both cases, the last child is the node for `last`.
  """
  if isinstance(node, astlib.Module):
    try:
      return node.body[-1]
    except IndexError:
      return None
  if isinstance(node, astlib.If):
    if (len(node.orelse) == 1 and isinstance(node.orelse[0], astlib.If) and
        fmt.get(node.orelse[0], 'is_elif')):
      return get_last_child(node.orelse[0], astlib)
    if node.orelse:
      return node.orelse[-1]
  elif isinstance(node, astlib.With):
    if (len(node.body) == 1 and isinstance(node.body[0], astlib.With) and
        fmt.get(node.body[0], 'is_continued')):
      return get_last_child(node.body[0], astlib)
  elif hasattr(astlib, 'Try') and isinstance(node, astlib.Try):
    if node.finalbody:
      return node.finalbody[-1]
    if node.orelse:
      return node.orelse[-1]
  elif hasattr(astlib, 'TryFinally') and isinstance(node, astlib.TryFinally):
    if node.finalbody:
      return node.finalbody[-1]
  elif hasattr(astlib, 'TryExcept') and isinstance(node, astlib.TryExcept):
    if node.orelse:
      return node.orelse[-1]
    if node.handlers:
      return get_last_child(node.handlers[-1], astlib)
  return node.body[-1]


def remove_child(parent, child, astlib=ast):

  for _, field_value in astlib.iter_fields(parent):
    if isinstance(field_value, list) and child in field_value:
      field_value.remove(child)
      return
  raise errors.InvalidAstError('Unable to find list containing child %r on '
                               'parent node %r' % (child, parent))


def replace_child(parent, node, replace_with):
  """Replace a node's child with another node while preserving formatting.

  Arguments:
    parent: (ast.AST) Parent node to replace a child of.
    node: (ast.AST) Child node to replace.
    replace_with: (ast.AST) New child node.
  """
  # TODO(soupytwist): Don't refer to the formatting dict directly
  if hasattr(node, fmt.PASTA_DICT):
    fmt.set(replace_with, 'prefix', fmt.get(node, 'prefix'))
    fmt.set(replace_with, 'suffix', fmt.get(node, 'suffix'))
  for field in parent._fields:
    field_val = getattr(parent, field, None)
    if field_val == node:
      setattr(parent, field, replace_with)
      return
    elif isinstance(field_val, list):
      try:
        field_val[field_val.index(node)] = replace_with
        return
      except ValueError:
        pass
  raise errors.InvalidAstError('Node %r is not a child of %r' % (node, parent))


def has_docstring(node, astlib=ast):
  return (hasattr(node, 'body') and node.body and
          (isinstance(node.body[0], astlib.Expr) or (
           hasattr(node.body[0], 'value') and
           isinstance(node.body[0].value, astlib.Str))))
