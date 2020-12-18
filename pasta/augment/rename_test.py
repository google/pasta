# coding=utf-8
"""Tests for augment.rename."""
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
from pasta.augment import rename
from pasta.base import scope
from pasta.base import test_utils


def suite(py_ver):

  class RenameTest(test_utils.TestCase):

    def test_rename_external_in_import(self):
      src = 'import aaa.bbb.ccc\naaa.bbb.ccc.foo()'
      t = pasta.ast_parse(src, py_ver)
      self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy', py_ver))
      self.checkAstsEqual(
          t, pasta.ast_parse('import xxx.yyy.ccc\nxxx.yyy.ccc.foo()', py_ver),
          py_ver)

      t = pasta.ast_parse(src, py_ver)
      self.assertTrue(
          rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy', py_ver))
      self.checkAstsEqual(
          t, pasta.ast_parse('import xxx.yyy\nxxx.yyy.foo()', py_ver), py_ver)

      t = pasta.ast_parse(src, py_ver)
      self.assertFalse(rename.rename_external(t, 'bbb', 'xxx.yyy', py_ver))
      self.checkAstsEqual(t, pasta.ast_parse(src, py_ver), py_ver)

    def test_rename_external_in_import_with_asname(self):
      src = 'import aaa.bbb.ccc as ddd\nddd.foo()'
      t = pasta.ast_parse(src, py_ver)
      self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy', py_ver))
      self.checkAstsEqual(
          t, pasta.ast_parse('import xxx.yyy.ccc as ddd\nddd.foo()', py_ver),
          py_ver)

    def test_rename_external_in_import_multiple_aliases(self):
      src = 'import aaa, aaa.bbb, aaa.bbb.ccc'
      t = pasta.ast_parse(src, py_ver)
      self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy', py_ver))
      self.checkAstsEqual(
          t, pasta.ast_parse('import aaa, xxx.yyy, xxx.yyy.ccc', py_ver),
          py_ver)

    def test_rename_external_in_importfrom(self):
      src = 'from aaa.bbb.ccc import ddd\nddd.foo()'
      t = pasta.ast_parse(src, py_ver)
      self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy', py_ver))
      self.checkAstsEqual(
          t, pasta.ast_parse('from xxx.yyy.ccc import ddd\nddd.foo()', py_ver),
          py_ver)

      t = pasta.ast_parse(src, py_ver)
      self.assertTrue(
          rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy', py_ver))
      self.checkAstsEqual(
          t, pasta.ast_parse('from xxx.yyy import ddd\nddd.foo()', py_ver),
          py_ver)

      t = pasta.ast_parse(src, py_ver)
      self.assertFalse(rename.rename_external(t, 'bbb', 'xxx.yyy', py_ver))
      self.checkAstsEqual(t, pasta.ast_parse(src, py_ver), py_ver)

    def test_rename_external_in_importfrom_alias(self):
      src = 'from aaa.bbb import ccc\nccc.foo()'
      t = pasta.ast_parse(src, py_ver)
      self.assertTrue(
          rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy', py_ver))
      self.checkAstsEqual(
          t, pasta.ast_parse('from xxx import yyy\nyyy.foo()', py_ver), py_ver)

    def test_rename_external_in_importfrom_alias_with_asname(self):
      src = 'from aaa.bbb import ccc as abc\nabc.foo()'
      t = pasta.ast_parse(src, py_ver)
      self.assertTrue(
          rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy', py_ver))
      self.checkAstsEqual(
          t, pasta.ast_parse('from xxx import yyy as abc\nabc.foo()', py_ver),
          py_ver)

    def test_rename_reads_name(self):
      src = 'aaa.bbb()'
      t = pasta.ast_parse(src, py_ver)
      sc = scope.analyze(t, py_ver)
      self.assertTrue(rename._rename_reads(sc, t, 'aaa', 'xxx', py_ver))
      self.checkAstsEqual(t, pasta.ast_parse('xxx.bbb()', py_ver), py_ver)

    def test_rename_reads_name_as_attribute(self):
      src = 'aaa.bbb()'
      t = pasta.ast_parse(src, py_ver)
      sc = scope.analyze(t, py_ver)
      rename._rename_reads(sc, t, 'aaa', 'xxx.yyy', py_ver)
      self.checkAstsEqual(t, pasta.ast_parse('xxx.yyy.bbb()', py_ver), py_ver)

    def test_rename_reads_attribute(self):
      src = 'aaa.bbb.ccc()'
      t = pasta.ast_parse(src, py_ver)
      sc = scope.analyze(t, py_ver)
      rename._rename_reads(sc, t, 'aaa.bbb', 'xxx.yyy', py_ver)
      self.checkAstsEqual(t, pasta.ast_parse('xxx.yyy.ccc()', py_ver), py_ver)

    def test_rename_reads_noop(self):
      src = 'aaa.bbb.ccc()'
      t = pasta.ast_parse(src, py_ver)
      sc = scope.analyze(t, py_ver)
      rename._rename_reads(sc, t, 'aaa.bbb.ccc.ddd', 'xxx.yyy', py_ver)
      rename._rename_reads(sc, t, 'bbb.aaa', 'xxx.yyy', py_ver)
      self.checkAstsEqual(t, pasta.ast_parse(src, py_ver), py_ver)

  @test_utils.requires_features('type_annotations', py_ver)
  def test_rename_reads_type_annotation(self):
    src = textwrap.dedent("""\
        def foo(bar: 'aaa.bbb.ccc.Bar'):
          pass
        """)
    t = ast.parse(src)
    sc = scope.analyze(t)
    rename._rename_reads(sc, t, 'aaa.bbb', 'xxx.yyy')
    self.checkAstsEqual(t, ast.parse(textwrap.dedent("""\
        def foo(bar: 'xxx.yyy.ccc.Bar'):
          pass
        """)))

  result = unittest.TestSuite()
  result.addTests(unittest.makeSuite(RenameTest))
  return result

if __name__ == '__main__':
  unittest.main()
