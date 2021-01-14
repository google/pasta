# coding=utf-8
"""Generate code from an annotated syntax tree."""
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
import six
import sys
import typed_ast
from typed_ast import ast27
from typed_ast import ast3

import pasta
from pasta.base import annotate
from pasta.base import formatting as fmt
from pasta.base import fstring_utils


class PrintError(Exception):
  """An exception for when we failed to print the tree."""


def to_str(tree, py_ver=sys.version_info[:2]):

  class Printer(annotate.get_base_visitor(py_ver)):
    """Traverses an AST and generates formatted python source code.

    This uses the same base visitor as annotating the AST, but instead of eating
    a
    token it spits one out. For special formatting information which was stored
    on
    the node, this is output exactly as it was read in unless one or more of the
    dependency attributes used to generate it has changed, in which case its
    default formatting is used.
    """

    def __init__(self):
      super(Printer, self).__init__()
      self.code = ''

    def visit(self, node):
      node._printer_info = collections.defaultdict(lambda: False)
      try:
        super(Printer, self).visit(node)
      except (TypeError, ValueError, IndexError, KeyError) as e:
        raise PrintError(e)
      del node._printer_info

    def visit_Module(self, node):
      self.prefix(node)
      bom = fmt.get(node, 'bom')
      if bom is not None:
        self.code += bom
      self.generic_visit(node)
      self.suffix(node)

    def visit_Num(self, node):
      self.prefix(node)
      content = fmt.get(node, 'content')
      self.code += content if content is not None else repr(node.n)
      self.suffix(node)

    def visit_Str(self, node):
      self.prefix(node)
      str_fmt = fmt.get(node, 'fmt')
      if str_fmt:
        self.code += str_fmt
      content = fmt.get(node, 'content')
      self.code += content if content is not None else repr(node.s)
      self.suffix(node)

    def visit_JoinedStr(self, node):
      self.prefix(node)
      content = fmt.get(node, 'content')

      if content is None:
        parts = []
        for val in node.values:
          if isinstance(val, ast27.Str) or isinstance(val, ast3.Str):
            parts.append(val.s)
          else:
            parts.append(fstring_utils.placeholder(len(parts)))
        content = repr(''.join(parts))

      values = [
          to_str(v, py_ver) for v in fstring_utils.get_formatted_values(node)
      ]
      self.code += fstring_utils.perform_replacements(content, values)
      self.suffix(node)

    def visit_Bytes(self, node):
      self.prefix(node)
      content = fmt.get(node, 'content')
      self.code += content if content is not None else repr(node.s)
      self.suffix(node)

    def visit_Constant(self, node):
      self.prefix(node)
      if node.value is Ellipsis:
        content = '...'
      else:
        content = fmt.get(node, 'content')
      self.code += content if content is not None else repr(node.s)
      self.suffix(node)

    def token(self, token_val,
             separate_before = False):
      """Emits a single token with exactly the given value.

      Arguments:
        token_val: the token to be emitted.
        separate_before: indicates whether it is necessary to separate the
          tokens parsed in this call from preceding text using whitespace.
      """
      if separate_before and self.code and self.code[-1].isalnum() and \
            (not token_val or token_val[0].isalnum()):
          self.code += ' '
      self.code += token_val

    def optional_token(self, node, attr_name, token_val,
                       allow_whitespace_prefix=False, default=False):
      del allow_whitespace_prefix
      value = fmt.get(node, attr_name)
      if value is None and default:
        value = token_val
      self.code += value or ''

    def attr(self, node, attr_name, attr_vals, deps=None, default=None):
      """Add the formatted data stored for a given attribute on this node.

      If any of the dependent attributes of the node have changed since it was
      annotated, then the stored formatted data for this attr_name is no longer
      valid, and we must use the default instead.

      Arguments:
        node: (ast.AST) An AST node to retrieve formatting information from.
        attr_name: (string) Name to load the formatting information from.
        attr_vals: (list of functions/strings) Unused here.
        deps: (optional, set of strings) Attributes of the node which the stored
          formatting data depends on.
        default: (string) Default formatted data for this attribute.
        separate_before: indicates whether it is necessary to separate the
          tokens parsed in this call from preceding text using whitespace.
      """
      del attr_vals
      if not hasattr(node, '_printer_info') or node._printer_info[attr_name]:
        return
      node._printer_info[attr_name] = True
      val = fmt.get(node, attr_name)
      if (val is None or deps and any(
          hasattr(node, dep + '__src') and
          (getattr(node, dep, None) != fmt.get(node, dep + '__src'))
          for dep in deps)):
        val = default

      val = val if val is not None else ''
      if separate_before and self.code and self.code[-1].isalnum() and \
            (not val or val[0].isalnum()):
          self.code += ' '
      self.code += val

    def check_is_elif(self, node):
      try:
        return fmt.get(node, 'is_elif')
      except AttributeError:
        return False

    def check_is_continued_try(self, node):
      # TODO: Don't set extra attributes on nodes
      return getattr(node, 'is_continued', False)

    def check_is_continued_with(self, node):
      # TODO: Don't set extra attributes on nodes
      return getattr(node, 'is_continued', False)

  """Convenient function to get the python source for an AST."""
  p = Printer()

  # Detect the most prevalent indentation style in the file and use it when
  # printing indented nodes which don't have formatting data.
  seen_indent_diffs = collections.defaultdict(lambda: 0)
  for node in pasta.ast_walk(tree, py_ver=py_ver):
    indent_diff = fmt.get(node, 'indent_diff', '')
    if indent_diff:
      seen_indent_diffs[indent_diff] += 1

  if seen_indent_diffs:
    indent_diff, _ = max(six.iteritems(seen_indent_diffs),
                         key=lambda tup: tup[1] if tup[0] else -1)
    p.set_default_indent_diff(indent_diff)

  p.visit(tree)
  return p.code


def to_tree_str(node, indent, py_ver=sys.version_info[:2]):
  """Returns a human-readable representation of the sub-tree rooted at node.

  This is a depth-first traversal of the tree that emits a string
  representation of each node and its fields, indenting the text of sub-trees
  based on their depth.
  """

  if hasattr(node, '__dict__'):
    print('%s%s' % (
        indent,
        ast27.dump(node) if py_ver < (3, 0) else ast3.dump(node),
    ))
    if hasattr(node, '__pasta__'):
      for attr in node.__pasta__.keys():
        print('%s  %s -> "%s"' % (indent, str(attr), str(node.__pasta__[attr])))
  elif isinstance(node, str) or isinstance(node, int):
    print('%s%s' % (indent, node))
    return
  else:
    print('%s%s' % (indent, node))

  for field, value in ast.iter_fields(node):
    print('%s%s' % (indent, field))
    if isinstance(value, list):
      for item in value:
        to_tree_str(item, py_ver, indent + '    ')
    elif value is not None:
      to_tree_str(value, py_ver, indent + '    ')
