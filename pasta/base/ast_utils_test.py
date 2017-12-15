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
