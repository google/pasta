# coding=utf-8
"""Tests for augment.extract."""
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
import textwrap
import unittest

import pasta
from pasta.augment import extract
from pasta.base import scope
from pasta.base import test_utils


class ExtractTest(test_utils.TestCase):

  def test_extract_trivial(self):
    src = 'x = 1\n'
    t = ast.parse(src)
    target_node = t.body[0]
    references = extract.extract_node(t, target_node, 'src')
    self.checkAstsEqual(t, ast.parse(''))
    self.assertEqual({}, references)

  def test_extract_with_dependencies(self):
    src = 'x = 1\na = x\n'
    t = ast.parse(src)
    target_node = t.body[1]
    references = extract.extract_node(t, target_node, 'src')
    self.checkAstsEqual(t, ast.parse('x = 1\n'))
    self.assertEqual({'x': 'src.x'}, references)

  def test_extract_with_imports(self):
    src = 'from bar.baz import x\na = x.y\n'
    t = ast.parse(src)
    target_node = t.body[1]
    references = extract.extract_node(t, target_node, 'src',
                                      cleanup_imports=False)
    self.checkAstsEqual(t, ast.parse(''))
    self.assertEqual({'x': 'bar.baz.x'}, references)

  def test_extract_cleanup_imports(self):
    src = 'from bar.baz import x\nfrom waz import wow\na = x.y\n'
    t = ast.parse(src)
    target_node = t.body[2]
    references = extract.extract_node(t, target_node, 'src',
                                      cleanup_imports=True)
    self.checkAstsEqual(t, ast.parse('from waz import wow\n'))
    self.assertEqual({'x': 'bar.baz.x'}, references)

  def test_extract_function(self):
    src = textwrap.dedent('''\
        from bar.baz import waz
        import blah
        x = blah.x
        def func():
          result = waz.wow()
          return result
        ''')
    t = ast.parse(src)
    target_node = t.body[3]
    references = extract.extract_node(t, target_node, 'src')
    self.checkAstsEqual(t, ast.parse(textwrap.dedent('''\
        import blah
        x = blah.x
        ''')))
    self.assertEqual({'waz': 'bar.baz.waz'}, references)

  def test_insert_trivial(self):
    t = ast.parse('')
    target_node = ast.parse('x = 1').body[0]
    references = {}
    extract.insert_node(t, target_node, references)
    self.checkAstsEqual(t, ast.parse('x = 1\n'))

  def test_insert_with_dependencies(self):
    t = ast.parse('')
    target_node = ast.parse('a = x').body[0]
    references = {'x': 'src.x'}
    extract.insert_node(t, target_node, references)
    self.checkAstsEqual(t, ast.parse('from src import x\na = x\n'))

  def test_insert_import_conflicts(self):
    t = ast.parse('x = True')
    target_node = ast.parse('a = x').body[0]
    references = {'x': 'src.x'}
    extract.insert_node(t, target_node, references)
    self.checkAstsEqual(
        t, ast.parse('from src import x as x_1\nx = True\na = x_1\n'))


def test_suite():
  result = unittest.TestSuite()
  result.addTests(unittest.makeSuite(ExtractTest))
  return result

if __name__ == '__main__':
  unittest.main()
