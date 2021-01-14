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

import sys
import typed_ast
from typed_ast import ast27
from typed_ast import ast3
import re

import pasta
from pasta.augment import errors
from pasta.base import formatting as fmt

# From PEP-0263 -- https://www.python.org/dev/peps/pep-0263/
_CODING_PATTERN = re.compile('^[ \t\v]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)')


_AST_OP_NODES = (ast27.And, ast27.Or, ast27.Eq, ast27.NotEq, ast27.Is,
                 ast27.IsNot, ast27.In, ast27.NotIn, ast27.Lt, ast27.LtE,
                 ast27.Gt, ast27.GtE, ast27.Add, ast27.Sub, ast27.Mult,
                 ast27.Div, ast27.Mod, ast27.Pow, ast27.LShift, ast27.RShift,
                 ast27.BitAnd, ast27.BitOr, ast27.BitXor, ast27.FloorDiv,
                 ast27.Invert, ast27.Not, ast27.UAdd, ast27.USub, ast3.And,
                 ast3.Or, ast3.Eq, ast3.NotEq, ast3.Is, ast3.IsNot, ast3.In,
                 ast3.NotIn, ast3.Lt, ast3.LtE, ast3.Gt, ast3.GtE, ast3.Add,
                 ast3.Sub, ast3.Mult, ast3.Div, ast3.Mod, ast3.Pow, ast3.LShift,
                 ast3.RShift, ast3.BitAnd, ast3.BitOr, ast3.BitXor,
                 ast3.FloorDiv, ast3.Invert, ast3.Not, ast3.UAdd, ast3.USub)


def parse(src, py_ver=sys.version_info[:2]):
  """Replaces typed_ast.parse; ensures additional properties on the parsed tree.

  This enforces the assumption that each node in the ast is unique.
  """

  class _TreeNormalizer(pasta.ast(py_ver).NodeTransformer):
    """Replaces all op nodes with unique instances."""

    def visit(self, node):
      if isinstance(node, _AST_OP_NODES):
        return node.__class__()
      return super(_TreeNormalizer, self).visit(node)

  tree=pasta.ast(py_ver).parse(sanitize_source(src))
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


def find_nodes_by_type(node, accept_types, py_ver=sys.version_info[:2]):
  visitor = get_find_node_visitor((lambda n: isinstance(n, accept_types)),
                                  py_ver=py_ver)
  visitor.visit(node)
  return visitor.results


def get_find_node_visitor(condition, py_ver=sys.version_info[:2]):

  class FindNodeVisitor(pasta.ast(py_ver).NodeVisitor):

    def __init__(self, condition):
      self._condition = condition
      self.results = []

    def visit(self, node):
      if self._condition(node):
        self.results.append(node)
      super(FindNodeVisitor, self).visit(node)

  return FindNodeVisitor(condition)


def get_last_child(node):
  """Get the last child node of a block statement.

  The input must be a block statement (e.g. ast.For, ast.With, etc).

  Examples:
    1. with first():
         second()
         last()

    2. try:
         first()
       except:
         second()
       finally:
         last()

  In both cases, the last child is the node for `last`.
  """
  if isinstance(node, ast27.Module) or isinstance(node, ast3.Module):
    try:
      return node.body[-1]
    except IndexError:
      return None
  if isinstance(node, ast27.If) or isinstance(node, ast3.If):
    if (len(node.orelse) == 1 and isinstance(node.orelse[0],
                                             (ast27.If, ast3.If)) and
        fmt.get(node.orelse[0], 'is_elif')):
      return get_last_child(node.orelse[0])
    if node.orelse:
      return node.orelse[-1]
  elif isinstance(node, ast27.With) or isinstance(node, ast3.With):
    if (len(node.body) == 1 and isinstance(node.body[0],
                                           (ast27.With, ast3.With)) and
        fmt.get(node.body[0], 'is_continued')):
      return get_last_child(node.body[0])
  elif isinstance(node, ast3.Try):
    if node.finalbody:
      return node.finalbody[-1]
    if node.orelse:
      return node.orelse[-1]
  elif isinstance(node, ast27.TryFinally):
    if node.finalbody:
      return node.finalbody[-1]
  elif isinstance(node, ast27.TryExcept):
    if node.orelse:
      return node.orelse[-1]
    if node.handlers:
      return get_last_child(node.handlers[-1])
  return node.body[-1]


def remove_child(parent, child):

  for _, field_value in pasta.ast(py_ver).iter_fields(parent):
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


def has_docstring(node):
  return (hasattr(node, 'body') and node.body and
          (isinstance(node.body[0], ast27.Expr) or
           isinstance(node.body[0], ast3.Expr)) and
          (isinstance(node.body[0].value, ast27.Str) or
           isinstance(node.body[0].value, ast3.Str)))
