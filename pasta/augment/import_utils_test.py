# coding=utf-8
"""Tests for import_utils."""
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
from typing import Tuple
from typed_ast import ast27
from typed_ast import ast3
import unittest

import pasta
from pasta.augment import import_utils
from pasta.base import ast_utils
from pasta.base import test_utils
from pasta.base import scope


def suite(py_ver: str):

  class SplitImportTest(test_utils.TestCase):

    def test_split_normal_import(self):
      src = 'import aaa, bbb, ccc\n'
      t = pasta.ast_parse(src, py_ver)
      import_node = t.body[0]
      sc = scope.analyze(t, py_ver)
      import_utils.split_import(sc, import_node, import_node.names[1])

      self.assertEqual(2, len(t.body))
      self.assertEqual(ast27.Import if py_ver < (3, 0) else ast3.Import,
                       type(t.body[1]))
      self.assertEqual([alias.name for alias in t.body[0].names],
                       ['aaa', 'ccc'])
      self.assertEqual([alias.name for alias in t.body[1].names], ['bbb'])

    def test_split_from_import(self):
      src = 'from aaa import bbb, ccc, ddd\n'
      t = pasta.ast_parse(src, py_ver)
      import_node = t.body[0]
      sc = scope.analyze(t, py_ver)
      import_utils.split_import(sc, import_node, import_node.names[1])

      self.assertEqual(2, len(t.body))
      self.assertEqual(ast27.ImportFrom if py_ver < (3, 0) else ast3.ImportFrom,
                       type(t.body[1]))
      self.assertEqual(t.body[0].module, 'aaa')
      self.assertEqual(t.body[1].module, 'aaa')
      self.assertEqual([alias.name for alias in t.body[0].names],
                       ['bbb', 'ddd'])

    def test_split_imports_with_alias(self):
      src = 'import aaa as a, bbb as b, ccc as c\n'
      t = pasta.ast_parse(src, py_ver)
      import_node = t.body[0]
      sc = scope.analyze(t, py_ver)
      import_utils.split_import(sc, import_node, import_node.names[1])

      self.assertEqual(2, len(t.body))
      self.assertEqual([alias.name for alias in t.body[0].names],
                       ['aaa', 'ccc'])
      self.assertEqual([alias.name for alias in t.body[1].names], ['bbb'])
      self.assertEqual(t.body[1].names[0].asname, 'b')

    def test_split_imports_multiple(self):
      src = 'import aaa, bbb, ccc\n'
      t = pasta.ast_parse(src, py_ver)
      import_node = t.body[0]
      alias_bbb = import_node.names[1]
      alias_ccc = import_node.names[2]
      sc = scope.analyze(t, py_ver)
      import_utils.split_import(sc, import_node, alias_bbb)
      import_utils.split_import(sc, import_node, alias_ccc)

      self.assertEqual(3, len(t.body))
      self.assertEqual([alias.name for alias in t.body[0].names], ['aaa'])
      self.assertEqual([alias.name for alias in t.body[1].names], ['ccc'])
      self.assertEqual([alias.name for alias in t.body[2].names], ['bbb'])

    def test_split_nested_imports(self):
      test_cases = (
          'def foo():\n  {import_stmt}\n',
          'class Foo(object):\n  {import_stmt}\n',
          'if foo:\n  {import_stmt}\nelse:\n  pass\n',
          'if foo:\n  pass\nelse:\n  {import_stmt}\n',
          'if foo:\n  pass\nelif bar:\n  {import_stmt}\n',
          'try:\n  {import_stmt}\nexcept:\n  pass\n',
          'try:\n  pass\nexcept:\n  {import_stmt}\n',
          'try:\n  pass\nfinally:\n  {import_stmt}\n',
          'for i in foo:\n  {import_stmt}\n',
          'for i in foo:\n  pass\nelse:\n  {import_stmt}\n',
          'while foo:\n  {import_stmt}\n',
      )

      for template in test_cases:
        try:
          src = template.format(import_stmt='import aaa, bbb, ccc')
          t = pasta.ast_parse(src, py_ver)
          sc = scope.analyze(t, py_ver)
          import_node = ast_utils.find_nodes_by_type(
              t, (ast27.Import, ast3.Import), py_ver)[0]
          import_utils.split_import(sc, import_node, import_node.names[1])

          split_import_nodes = ast_utils.find_nodes_by_type(
              t, (ast27.Import, ast3.Import), py_ver)
          self.assertEqual(1, len(t.body))
          self.assertEqual(2, len(split_import_nodes))
          self.assertEqual(
              [alias.name for alias in split_import_nodes[0].names],
              ['aaa', 'ccc'])
          self.assertEqual(
              [alias.name for alias in split_import_nodes[1].names], ['bbb'])
        except:
          self.fail('Failed while executing case:\n%s\nCaused by:\n%s' %
                    (src, traceback.format_exc()))

  class GetUnusedImportsTest(test_utils.TestCase):

    def test_normal_imports(self):
      src = """\
import a
import b
a.foo()
  """
      tree = pasta.ast_parse(src, py_ver)
      self.assertItemsEqual(
          import_utils.get_unused_import_aliases(tree, py_ver),
          [tree.body[1].names[0]])

    def test_import_from(self):
      src = """\
from my_module import a
import b
from my_module import c
b.foo()
c.bar()
  """
      tree = pasta.ast_parse(src, py_ver)
      self.assertItemsEqual(
          import_utils.get_unused_import_aliases(tree, py_ver),
          [tree.body[0].names[0]])

    def test_import_from_alias(self):
      src = """\
from my_module import a, b
b.foo()
  """
      tree = pasta.ast_parse(src, py_ver)
      self.assertItemsEqual(
          import_utils.get_unused_import_aliases(tree, py_ver),
          [tree.body[0].names[0]])

    def test_import_asname(self):
      src = """\
from my_module import a as a_mod, b as unused_b_mod
import c as c_mod, d as unused_d_mod
a_mod.foo()
c_mod.foo()
  """
      tree = pasta.ast_parse(src, py_ver)
      self.assertItemsEqual(
          import_utils.get_unused_import_aliases(tree, py_ver),
          [tree.body[0].names[1], tree.body[1].names[1]])

    def test_dynamic_import(self):
      # For now we just don't want to error out on these, longer
      # term we want to do the right thing (see
      # https://github.com/google/pasta/issues/32)
      src = """\
def foo():
  import bar
  """
      tree = pasta.ast_parse(src, py_ver)
      self.assertItemsEqual(
          import_utils.get_unused_import_aliases(tree, py_ver), [])

  class RemoveImportTest(test_utils.TestCase):
    # Note that we don't test any 'asname' examples but as far as
    # remove_import_alias_node is concerned it's not a different case because
    # its still just an alias type and we don't care about the internals of
    # the alias we're trying to remove.
    def test_remove_just_alias(self):
      src = 'import a, b'
      tree = pasta.ast_parse(src, py_ver)
      sc = scope.analyze(tree, py_ver)

      unused_b_node = tree.body[0].names[1]

      import_utils.remove_import_alias_node(sc, unused_b_node)

      self.assertEqual(len(tree.body), 1)
      if py_ver < (3, 0):
        self.assertEqual(type(tree.body[0]), ast27.Import)
      else:
        self.assertEqual(type(tree.body[0]), ast3.Import)
      self.assertEqual(len(tree.body[0].names), 1)
      self.assertEqual(tree.body[0].names[0].name, 'a')

    def test_remove_just_alias_import_from(self):
      src = 'from m import a, b'
      tree = pasta.ast_parse(src, py_ver)
      sc = scope.analyze(tree, py_ver)

      unused_b_node = tree.body[0].names[1]

      import_utils.remove_import_alias_node(sc, unused_b_node)

      self.assertEqual(len(tree.body), 1)
      if py_ver < (3, 0):
        self.assertEqual(type(tree.body[0]), ast27.ImportFrom)
      else:
        self.assertEqual(type(tree.body[0]), ast3.ImportFrom)
      self.assertEqual(len(tree.body[0].names), 1)
      self.assertEqual(tree.body[0].names[0].name, 'a')

    def test_remove_full_import(self):
      src = 'import a'
      tree = pasta.ast_parse(src, py_ver)
      sc = scope.analyze(tree, py_ver)

      a_node = tree.body[0].names[0]

      import_utils.remove_import_alias_node(sc, a_node)

      self.assertEqual(len(tree.body), 0)

    def test_remove_full_importfrom(self):
      src = 'from m import a'
      tree = pasta.ast_parse(src, py_ver)
      sc = scope.analyze(tree, py_ver)

      a_node = tree.body[0].names[0]

      import_utils.remove_import_alias_node(sc, a_node)

      self.assertEqual(len(tree.body), 0)

  class AddImportTest(test_utils.TestCase):

    def test_add_normal_import(self):
      tree = pasta.ast_parse('', py_ver)
      self.assertEqual(
          'a.b.c',
          import_utils.add_import(tree, 'a.b.c', py_ver, from_import=False))
      self.assertEqual('import a.b.c\n', pasta.dump(tree, py_ver))

    def test_add_normal_import_with_asname(self):
      tree = pasta.ast_parse('', py_ver)
      self.assertEqual(
          'd',
          import_utils.add_import(
              tree, 'a.b.c', py_ver, asname='d', from_import=False))
      self.assertEqual('import a.b.c as d\n', pasta.dump(tree, py_ver))

    def test_add_from_import(self):
      tree = pasta.ast_parse('', py_ver)
      self.assertEqual(
          'c', import_utils.add_import(tree, 'a.b.c', py_ver, from_import=True))
      self.assertEqual('from a.b import c\n', pasta.dump(tree, py_ver))

    def test_add_from_import_with_asname(self):
      tree = pasta.ast_parse('', py_ver)
      self.assertEqual(
          'd',
          import_utils.add_import(
              tree, 'a.b.c', py_ver, asname='d', from_import=True))
      self.assertEqual('from a.b import c as d\n', pasta.dump(tree, py_ver))

    def test_add_single_name_from_import(self):
      tree = pasta.ast_parse('', py_ver)
      self.assertEqual(
          'foo', import_utils.add_import(tree, 'foo', py_ver, from_import=True))
      self.assertEqual('import foo\n', pasta.dump(tree, py_ver))

    def test_add_single_name_from_import_with_asname(self):
      tree = pasta.ast_parse('', py_ver)
      self.assertEqual(
          'bar',
          import_utils.add_import(
              tree, 'foo', py_ver, asname='bar', from_import=True))
      self.assertEqual('import foo as bar\n', pasta.dump(tree, py_ver))

    def test_add_existing_import(self):
      tree = pasta.ast_parse('from a.b import c', py_ver)
      self.assertEqual('c', import_utils.add_import(tree, 'a.b.c', py_ver))
      self.assertEqual('from a.b import c\n', pasta.dump(tree, py_ver))

    def test_add_existing_import_aliased(self):
      tree = pasta.ast_parse('from a.b import c as d', py_ver)
      self.assertEqual('d', import_utils.add_import(tree, 'a.b.c', py_ver))
      self.assertEqual('from a.b import c as d\n', pasta.dump(tree, py_ver))

    def test_add_existing_import_aliased_with_asname(self):
      tree = pasta.ast_parse('from a.b import c as d', py_ver)
      self.assertEqual(
          'd', import_utils.add_import(tree, 'a.b.c', py_ver, asname='e'))
      self.assertEqual('from a.b import c as d\n', pasta.dump(tree, py_ver))

    def test_add_existing_import_normal_import(self):
      tree = pasta.ast_parse('import a.b.c', py_ver)
      self.assertEqual(
          'a.b',
          import_utils.add_import(tree, 'a.b', py_ver, from_import=False))
      self.assertEqual('import a.b.c\n', pasta.dump(tree, py_ver))

    def test_add_existing_import_normal_import_aliased(self):
      tree = pasta.ast_parse('import a.b.c as d', py_ver)
      self.assertEqual(
          'a.b',
          import_utils.add_import(tree, 'a.b', py_ver, from_import=False))
      self.assertEqual(
          'd',
          import_utils.add_import(tree, 'a.b.c', py_ver, from_import=False))
      self.assertEqual('import a.b\nimport a.b.c as d\n',
                       pasta.dump(tree, py_ver))

    def test_add_import_with_conflict(self):
      tree = pasta.ast_parse('def c(): pass\n', py_ver)
      self.assertEqual(
          'c_1',
          import_utils.add_import(tree, 'a.b.c', py_ver, from_import=True))
      self.assertEqual('from a.b import c as c_1\ndef c():\n  pass\n',
                       pasta.dump(tree, py_ver))

    def test_add_import_with_asname_with_conflict(self):
      tree = pasta.ast_parse('def c(): pass\n', py_ver)
      self.assertEqual(
          'c_1',
          import_utils.add_import(
              tree, 'a.b', py_ver, asname='c', from_import=True))
      self.assertEqual('from a import b as c_1\ndef c():\n  pass\n',
                       pasta.dump(tree, py_ver))

    def test_merge_from_import(self):
      tree = pasta.ast_parse('from a.b import c', py_ver)

      # x is explicitly not merged
      self.assertEqual(
          'x',
          import_utils.add_import(
              tree, 'a.b.x', py_ver, merge_from_imports=False))
      self.assertEqual('from a.b import x\nfrom a.b import c\n',
                       pasta.dump(tree, py_ver))

      # y is allowed to be merged and is grouped into the first matching import
      self.assertEqual(
          'y',
          import_utils.add_import(
              tree, 'a.b.y', py_ver, merge_from_imports=True))
      self.assertEqual('from a.b import x, y\nfrom a.b import c\n',
                       pasta.dump(tree, py_ver))

    def test_add_import_after_docstring(self):
      tree = pasta.parse('\'Docstring.\'\n', py_ver)
      self.assertEqual('a', import_utils.add_import(tree, 'a', py_ver))
      self.assertEqual('\'Docstring.\'\nimport a\n', pasta.dump(tree, py_ver))

  class RemoveDuplicatesTest(test_utils.TestCase):

    def test_remove_duplicates(self):
      src = """
import a
import b
import c
import b
import d
  """
      tree = pasta.ast_parse(src, py_ver)
      self.assertTrue(import_utils.remove_duplicates(tree, py_ver))

      self.assertEqual(len(tree.body), 4)
      self.assertEqual(tree.body[0].names[0].name, 'a')
      self.assertEqual(tree.body[1].names[0].name, 'b')
      self.assertEqual(tree.body[2].names[0].name, 'c')
      self.assertEqual(tree.body[3].names[0].name, 'd')

    def test_remove_duplicates_multiple(self):
      src = """
import a, b
import b, c
import d, a, e, f
  """
      tree = pasta.ast_parse(src, py_ver)
      self.assertTrue(import_utils.remove_duplicates(tree, py_ver))

      self.assertEqual(len(tree.body), 3)
      self.assertEqual(len(tree.body[0].names), 2)
      self.assertEqual(tree.body[0].names[0].name, 'a')
      self.assertEqual(tree.body[0].names[1].name, 'b')
      self.assertEqual(len(tree.body[1].names), 1)
      self.assertEqual(tree.body[1].names[0].name, 'c')
      self.assertEqual(len(tree.body[2].names), 3)
      self.assertEqual(tree.body[2].names[0].name, 'd')
      self.assertEqual(tree.body[2].names[1].name, 'e')
      self.assertEqual(tree.body[2].names[2].name, 'f')

    def test_remove_duplicates_empty_node(self):
      src = """
import a, b, c
import b, c
  """
      tree = pasta.ast_parse(src, py_ver)
      self.assertTrue(import_utils.remove_duplicates(tree, py_ver))

      self.assertEqual(len(tree.body), 1)
      self.assertEqual(len(tree.body[0].names), 3)
      self.assertEqual(tree.body[0].names[0].name, 'a')
      self.assertEqual(tree.body[0].names[1].name, 'b')
      self.assertEqual(tree.body[0].names[2].name, 'c')

    def test_remove_duplicates_normal_and_from(self):
      src = """
import a.b
from a import b
  """
      tree = pasta.ast_parse(src, py_ver)
      self.assertFalse(import_utils.remove_duplicates(tree, py_ver))
      self.assertEqual(len(tree.body), 2)

    def test_remove_duplicates_aliases(self):
      src = """
import a
import a as ax
import a as ax2
import a as ax
  """
      tree = pasta.ast_parse(src, py_ver)
      self.assertTrue(import_utils.remove_duplicates(tree, py_ver))
      self.assertEqual(len(tree.body), 3)
      self.assertEqual(tree.body[0].names[0].asname, None)
      self.assertEqual(tree.body[1].names[0].asname, 'ax')
      self.assertEqual(tree.body[2].names[0].asname, 'ax2')

  result = unittest.TestSuite()
  result.addTests(unittest.makeSuite(SplitImportTest))
  result.addTests(unittest.makeSuite(GetUnusedImportsTest))
  result.addTests(unittest.makeSuite(RemoveImportTest))
  result.addTests(unittest.makeSuite(AddImportTest))
  result.addTests(unittest.makeSuite(RemoveDuplicatesTest))
  return result

if __name__ == '__main__':
  unittest.main()
