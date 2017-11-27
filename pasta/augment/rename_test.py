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
import unittest

from pasta.augment import rename
from pasta.base import test_utils


class RenameTest(test_utils.TestCase):

  def test_rename_external_in_import(self):
    src = 'import aaa.bbb.ccc\n'
    t = ast.parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy'))
    self.assertEqual(t.body[0].names[0].name, 'xxx.yyy.ccc')

    t = ast.parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy'))
    self.assertEqual(t.body[0].names[0].name, 'xxx.yyy')

    t = ast.parse(src)
    self.assertFalse(rename.rename_external(t, 'bbb', 'xxx.yyy'))
    self.assertEqual(t.body[0].names[0].name, 'aaa.bbb.ccc')

  def test_rename_external_in_import_with_asname(self):
    src = 'import aaa.bbb.ccc as ddd\n'
    t = ast.parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy'))
    self.assertEqual(t.body[0].names[0].name, 'xxx.yyy.ccc')
    self.assertEqual(t.body[0].names[0].asname, 'ddd')

  def test_rename_external_in_import_multiple_aliases(self):
    src = 'import aaa, aaa.bbb, aaa.bbb.ccc\n'
    t = ast.parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy'))
    self.assertEqual(t.body[0].names[0].name, 'aaa')
    self.assertEqual(t.body[0].names[1].name, 'xxx.yyy')
    self.assertEqual(t.body[0].names[2].name, 'xxx.yyy.ccc')

  def test_rename_external_in_importfrom(self):
    src = 'from aaa.bbb.ccc import ddd\n'
    t = ast.parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb', 'xxx.yyy'))
    self.assertEqual(t.body[0].module, 'xxx.yyy.ccc')

    t = ast.parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy'))
    self.assertEqual(t.body[0].module, 'xxx.yyy')

    t = ast.parse(src)
    self.assertFalse(rename.rename_external(t, 'bbb', 'xxx.yyy'))
    self.assertEqual(t.body[0].module, 'aaa.bbb.ccc')

  def test_rename_external_in_importfrom_alias(self):
    src = 'from aaa.bbb import ccc\n'
    t = ast.parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy'))
    self.assertEqual(t.body[0].module, 'xxx')
    self.assertEqual(t.body[0].names[0].name, 'yyy')

  def test_rename_external_in_importfrom_alias_with_asname(self):
    src = 'from aaa.bbb import ccc as abc\n'
    t = ast.parse(src)
    self.assertTrue(rename.rename_external(t, 'aaa.bbb.ccc', 'xxx.yyy'))
    self.assertEqual(t.body[0].module, 'xxx')
    self.assertEqual(t.body[0].names[0].name, 'yyy')
    self.assertEqual(t.body[0].names[0].asname, 'abc')


def suite():
  result = unittest.TestSuite()
  result.addTests(unittest.makeSuite(RenameTest))
  return result

if __name__ == '__main__':
  unittest.main()
