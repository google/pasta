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
import contextlib
import itertools

from pasta.base import annotate
from pasta.base import ast_utils

# TODO: Handle indentation correctly on inserted nodes


class Printer(annotate.BaseVisitor):

  def __init__(self):
    self.code = ''

  def visit(self, node):
#    if isinstance(node, ast.Name):
#      print(node.__class__.__name__, node.id, dict(node.a))
#    else:
#      print(node.__class__.__name__, dict(node.a))
    try:
      node._printer_info = collections.defaultdict(lambda: False)
    except AttributeError:
      pass # fails for primitive types
    super(Printer, self).visit(node)
    del node._printer_info

  def visit_Num(self, node):
    self.prefix(node)
    self.code += node.a.get('content', repr(node.n))
    self.suffix(node)

  def token(self, value):
    self.code += value

  def optional_suffix(self, node, name, unused_val):
    if not hasattr(node, 'a'):
      return
    self.code += ast_utils.prop(node, name)

  def attr(self, node, attr_name, unused_attr_vals, deps=None, default=''):
    if not hasattr(node, '_printer_info') or node._printer_info[attr_name]:
      return
    node._printer_info[attr_name] = True
    if (deps and
        any(getattr(node, dep, None) != ast_utils.prop(node, dep + '__src')
            for dep in deps)):
      self.code += default
    else:
      val = ast_utils.prop(node, attr_name)
      self.code += val if val is not None else default

  def check_is_elif(self, node):
    try:
      return ast_utils.prop(node, 'is_elif')
    except AttributeError:
      return False

  def check_is_continued_with(self, node):
    # TODO: Don't set extra attributes on nodes
    return getattr(node, 'is_continued', False)


def to_str(tree):
  p = Printer()
  p.visit(tree)
  return p.code
