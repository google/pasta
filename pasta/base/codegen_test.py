# coding=utf-8
"""Tests for generating code from a non-annotated ast."""
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


class AutoFormatTest(unittest.TestCase):
  """Tests that code without formatting info is printed neatly."""

  def test_imports(self):
    src = 'from a import b\nimport c, d\nfrom ..e import f, g\n'
    t = ast.parse(src)
    self.assertEqual(src, pasta.dump(t))

  def test_function(self):
    t = ast.parse('def a(b, c): d')
    self.assertEqual('def a(b, c):\n  d\n', pasta.dump(t))

  def test_functions_nested(self):
    src = textwrap.dedent('''\
        def a(b, c):
          def d(e): f
          g
          def h(): i
          j
        ''')
    formatted_src = textwrap.dedent('''\
        def a(b, c):
          def d(e):
            f
          g
          def h():
            i
          j
        ''')
    t = ast.parse(src)
    self.assertEqual(formatted_src, pasta.dump(t))

  def test_class(self):
    t = ast.parse('class A(b, c): d')
    self.assertEqual('class A(b, c):\n  d\n', pasta.dump(t))

  def test_classes_nested(self):
    src = textwrap.dedent('''\
        class A(b, c):
          def d(self, e): f
          class G: h
        ''')
    formatted_src = textwrap.dedent('''\
        class A(b, c):
          def d(self, e):
            f
          class G():
            h
        ''')
    t = ast.parse(src)
    self.assertEqual(formatted_src, pasta.dump(t))


def suite():
  result = unittest.TestSuite()
  result.addTests(unittest.makeSuite(AutoFormatTest))
  return result


if __name__ == '__main__':
  unittest.main()
