# coding=utf-8
"""Tests for ast_utils."""
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
import traceback
import unittest

import pasta
from pasta.base import ast_utils
from pasta.base import test_utils
from pasta.base import scope


class UtilsTest(test_utils.TestCase):

  def test_get_argument_count(self):
    test_cases = (
        (0, 'def foo(): pass'),
        (1, 'def foo(a): pass'),
        (2, 'def foo(a, b=2): pass'),
        (2, 'def foo(a=1, b=2): pass'),
        (3, 'def foo(a, b=2, c=3): pass'),
        (3, 'def foo(a, b=2, *c): pass'),
        (4, 'def foo(a, b=2, *c, **d): pass'),
        (3, 'def foo(a, b=2, **d): pass'),
        (1, 'def foo(*c): pass'),
        (1, 'def foo(**d): pass'),
    )
    for argument_count, src in test_cases:
      t = ast.parse(src)
      self.assertEqual(argument_count,
                       ast_utils.get_argument_count(t.body[0].args))

  def test_sanitize_source(self):
    coding_lines = (
        '# -*- coding: latin-1 -*-',
        '# -*- coding: iso-8859-15 -*-',
        '# vim: set fileencoding=ascii :',
        '# This Python file uses the following encoding: utf-8',
    )
    src_template = '{coding}\na = 123\n'
    sanitized_src = '# (removed coding)\na = 123\n'
    for line in coding_lines:
      src = src_template.format(coding=line)

      # Replaced on lines 1 and 2
      self.assertEqual(sanitized_src, ast_utils.sanitize_source(src))
      src_prefix = '"""Docstring."""\n'
      self.assertEqual(src_prefix + sanitized_src,
                       ast_utils.sanitize_source(src_prefix + src))

      # Unchanged on line 3
      src_prefix = '"""Docstring."""\n# line 2\n'
      self.assertEqual(src_prefix + src,
                       ast_utils.sanitize_source(src_prefix + src))


class RemoveChildTest(test_utils.TestCase):

  def testRemoveChildMethod(self):
    src = """\
class C():
  def f(x):
    return x + 2
  def g(x):
    return x + 3
"""
    tree = pasta.parse(src)
    class_node = tree.body[0]
    meth1_node = class_node.body[0]

    ast_utils.remove_child(class_node, meth1_node)

    result = pasta.dump(tree)
    expected = """\
class C():
  def g(x):
    return x + 3
"""
    self.assertEqual(result, expected)

  def testRemoveAlias(self):
    src = "from a import b, c"
    tree = pasta.parse(src)
    import_node = tree.body[0]
    alias1 = import_node.names[0]
    ast_utils.remove_child(import_node, alias1)

    self.assertEqual(pasta.dump(tree), "from a import c")

  def testRemoveFromBlock(self):
    src = """\
if a:
  print("foo!")
  x = 1
"""
    tree = pasta.parse(src)
    if_block = tree.body[0]
    print_stmt = if_block.body[0]
    ast_utils.remove_child(if_block, print_stmt)

    expected = """\
if a:
  x = 1
"""
    self.assertEqual(pasta.dump(tree), expected)
