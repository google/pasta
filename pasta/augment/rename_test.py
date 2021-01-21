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
import sys
import textwrap
import unittest

import pasta
from pasta.augment import rename
from pasta.base import scope
from pasta.base import test_utils


class RenameTest(test_utils.TestCase):

  def test_rename_external_in_import(self):
    src = 'import aaa.bbb.ccc\naaa.bbb.ccc.foo()'
    t = pasta.ast_parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy'))
    self.checkAstsEqual(
        t, pasta.ast_parse('import xxx.yyy.ccc\nxxx.yyy.ccc.foo()'))

    t = pasta.ast_parse(src)
    self.assertTrue(
        rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy'))
    self.checkAstsEqual(
        t, pasta.ast_parse('import xxx.yyy\nxxx.yyy.foo()'))

    t = pasta.ast_parse(src)
    self.assertFalse(rename.rename_external(t, 'bbb', 'xxx.yyy'))
    self.checkAstsEqual(t, pasta.ast_parse(src))

  def test_rename_external_in_import_with_asname(self):
    src = 'import aaa.bbb.ccc as ddd\nddd.foo()'
    t = pasta.ast_parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy'))
    self.checkAstsEqual(
        t, pasta.ast_parse('import xxx.yyy.ccc as ddd\nddd.foo()'))

  def test_rename_external_in_import_multiple_aliases(self):
    src = 'import aaa, aaa.bbb, aaa.bbb.ccc'
    t = pasta.ast_parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy'))
    self.checkAstsEqual(
        t, pasta.ast_parse('import aaa, xxx.yyy, xxx.yyy.ccc'))

  def test_rename_external_in_importfrom(self):
    src = 'from aaa.bbb.ccc import ddd\nddd.foo()'
    t = pasta.ast_parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy'))
    self.checkAstsEqual(
        t, pasta.ast_parse('from xxx.yyy.ccc import ddd\nddd.foo()'))

    t = pasta.ast_parse(src)
    self.assertTrue(
        rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy'))
    self.checkAstsEqual(
        t, pasta.ast_parse('from xxx.yyy import ddd\nddd.foo()'))

    t = pasta.ast_parse(src)
    self.assertFalse(rename.rename_external(t, 'bbb', 'xxx.yyy'))
    self.checkAstsEqual(t, pasta.ast_parse(src))

  def test_rename_external_in_importfrom_alias(self):
    src = 'from aaa.bbb import ccc\nccc.foo()'
    t = pasta.ast_parse(src)
    self.assertTrue(
        rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy'))
    self.checkAstsEqual(
        t, pasta.ast_parse('from xxx import yyy\nyyy.foo()'))

  def test_rename_external_in_importfrom_alias_with_asname(self):
    src = 'from aaa.bbb import ccc as abc\nabc.foo()'
    t = pasta.ast_parse(src)
    self.assertTrue(
        rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy'))
    self.checkAstsEqual(
        t, pasta.ast_parse('from xxx import yyy as abc\nabc.foo()'))

  def test_rename_reads_name(self):
    src = 'aaa.bbb()'
    t = pasta.ast_parse(src)
    sc = scope.analyze(t)
    self.assertTrue(rename._rename_reads(sc, t, 'aaa', 'xxx'))
    self.checkAstsEqual(t, pasta.ast_parse('xxx.bbb()'))

  def test_rename_reads_name_as_attribute(self):
    src = 'aaa.bbb()'
    t = pasta.ast_parse(src)
    sc = scope.analyze(t)
    rename._rename_reads(sc, t, 'aaa', 'xxx.yyy')
    self.checkAstsEqual(t, pasta.ast_parse('xxx.yyy.bbb()'))

  def test_rename_reads_attribute(self):
    src = 'aaa.bbb.ccc()'
    t = pasta.ast_parse(src)
    sc = scope.analyze(t)
    rename._rename_reads(sc, t, 'aaa.bbb', 'xxx.yyy')
    self.checkAstsEqual(t, pasta.ast_parse('xxx.yyy.ccc()'))

  def test_rename_reads_noop(self):
    src = 'aaa.bbb.ccc()'
    t = pasta.ast_parse(src)
    sc = scope.analyze(t)
    rename._rename_reads(sc, t, 'aaa.bbb.ccc.ddd', 'xxx.yyy')
    rename._rename_reads(sc, t, 'bbb.aaa', 'xxx.yyy')
    self.checkAstsEqual(t, pasta.ast_parse(src))

  @test_utils.requires_features('type_annotations')
  def test_rename_reads_type_annotation(self):
    src = textwrap.dedent("""\
        def foo(bar: 'aaa.bbb.ccc.Bar'):
          pass
        """)
    t = pasta.ast_parse(src)
    sc = scope.analyze(t)
    rename._rename_reads(sc, t, 'aaa.bbb', 'xxx.yyy')
    self.checkAstsEqual(t, pasta.ast_parse(textwrap.dedent("""\
        def foo(bar: 'xxx.yyy.ccc.Bar'):
          pass
        """)))


if __name__ == '__main__':
  unittest.main()
