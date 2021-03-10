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
import sys
import traceback
import unittest

import pasta
from pasta.augment import import_utils
from pasta.base import ast_utils
from pasta.base import test_utils
from pasta.base import scope

astlib = getattr(pasta, 'TEST_ASTLIB', ast)


class SplitImportTest(test_utils.TestCase):

  def test_split_normal_import(self):
    src = 'import aaa, bbb, ccc\n'
    t = astlib.parse(src)
    import_node = t.body[0]
    sc = scope.analyze(t, astlib=astlib)
    import_utils.split_import(sc, import_node, import_node.names[1])

    self.assertEqual(2, len(t.body))
    self.assertEqual(astlib.Import, type(t.body[1]))
    self.assertEqual([alias.name for alias in t.body[0].names],
                     ['aaa', 'ccc'])
    self.assertEqual([alias.name for alias in t.body[1].names], ['bbb'])

  def test_split_from_import(self):
    src = 'from aaa import bbb, ccc, ddd\n'
    t = astlib.parse(src)
    import_node = t.body[0]
    sc = scope.analyze(t, astlib=astlib)
    import_utils.split_import(sc, import_node, import_node.names[1])

    self.assertEqual(2, len(t.body))
    self.assertEqual(astlib.ImportFrom, type(t.body[1]))
    self.assertEqual(t.body[0].module, 'aaa')
    self.assertEqual(t.body[1].module, 'aaa')
    self.assertEqual([alias.name for alias in t.body[0].names],
                     ['bbb', 'ddd'])

  def test_split_imports_with_alias(self):
    src = 'import aaa as a, bbb as b, ccc as c\n'
    t = astlib.parse(src)
    import_node = t.body[0]
    sc = scope.analyze(t, astlib=astlib)
    import_utils.split_import(sc, import_node, import_node.names[1])

    self.assertEqual(2, len(t.body))
    self.assertEqual([alias.name for alias in t.body[0].names],
                     ['aaa', 'ccc'])
    self.assertEqual([alias.name for alias in t.body[1].names], ['bbb'])
    self.assertEqual(t.body[1].names[0].asname, 'b')

  def test_split_imports_multiple(self):
    src = 'import aaa, bbb, ccc\n'
    t = astlib.parse(src)
    import_node = t.body[0]
    alias_bbb = import_node.names[1]
    alias_ccc = import_node.names[2]
    sc = scope.analyze(t, astlib=astlib)
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
        t = astlib.parse(src)
        sc = scope.analyze(t, astlib=astlib)
        import_node = ast_utils.find_nodes_by_type(
            t, astlib.Import, astlib=astlib)[0]
        import_utils.split_import(sc, import_node, import_node.names[1])

        split_import_nodes = ast_utils.find_nodes_by_type(
            t, astlib.Import, astlib=astlib)
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
    tree = astlib.parse(src)
    self.assertItemsEqual(
        import_utils.get_unused_import_aliases(tree, astlib=astlib),
        [tree.body[1].names[0]])

  def test_import_from(self):
    src = """\
from my_module import a
import b
from my_module import c
b.foo()
c.bar()
"""
    tree = astlib.parse(src)
    self.assertItemsEqual(
        import_utils.get_unused_import_aliases(tree, astlib=astlib),
        [tree.body[0].names[0]])

  def test_import_from_alias(self):
    src = """\
from my_module import a, b
b.foo()
"""
    tree = astlib.parse(src)
    self.assertItemsEqual(
        import_utils.get_unused_import_aliases(tree, astlib=astlib),
        [tree.body[0].names[0]])

  def test_import_asname(self):
    src = """\
from my_module import a as a_mod, b as unused_b_mod
import c as c_mod, d as unused_d_mod
a_mod.foo()
c_mod.foo()
"""
    tree = astlib.parse(src)
    self.assertItemsEqual(
        import_utils.get_unused_import_aliases(tree, astlib=astlib),
        [tree.body[0].names[1], tree.body[1].names[1]])

  def test_dynamic_import(self):
    # For now we just don't want to error out on these, longer
    # term we want to do the right thing (see
    # https://github.com/google/pasta/issues/32)
    src = """\
def foo():
  import bar
"""
    tree = astlib.parse(src)
    self.assertItemsEqual(
        import_utils.get_unused_import_aliases(tree, astlib=astlib), [])

class RemoveImportTest(test_utils.TestCase):
  # Note that we don't test any 'asname' examples but as far as
  # remove_import_alias_node is concerned it's not a different case because
  # its still just an alias type and we don't care about the internals of
  # the alias we're trying to remove.
  def test_remove_just_alias(self):
    src = 'import a, b'
    tree = astlib.parse(src)
    sc = scope.analyze(tree, astlib=astlib)

    unused_b_node = tree.body[0].names[1]

    import_utils.remove_import_alias_node(sc, unused_b_node, astlib=astlib)

    self.assertEqual(len(tree.body), 1)
    self.assertEqual(type(tree.body[0]), astlib.Import)
    self.assertEqual(len(tree.body[0].names), 1)
    self.assertEqual(tree.body[0].names[0].name, 'a')

  def test_remove_just_alias_import_from(self):
    src = 'from m import a, b'
    tree = astlib.parse(src)
    sc = scope.analyze(tree, astlib=astlib)

    unused_b_node = tree.body[0].names[1]

    import_utils.remove_import_alias_node(sc, unused_b_node, astlib=astlib)

    self.assertEqual(len(tree.body), 1)
    self.assertEqual(type(tree.body[0]), astlib.ImportFrom)
    self.assertEqual(len(tree.body[0].names), 1)
    self.assertEqual(tree.body[0].names[0].name, 'a')

  def test_remove_full_import(self):
    src = 'import a'
    tree = astlib.parse(src)
    sc = scope.analyze(tree, astlib=astlib)

    a_node = tree.body[0].names[0]

    import_utils.remove_import_alias_node(sc, a_node, astlib=astlib)

    self.assertEqual(len(tree.body), 0)

  def test_remove_full_importfrom(self):
    src = 'from m import a'
    tree = astlib.parse(src)
    sc = scope.analyze(tree, astlib=astlib)

    a_node = tree.body[0].names[0]

    import_utils.remove_import_alias_node(sc, a_node, astlib=astlib)

    self.assertEqual(len(tree.body), 0)

class AddImportTest(test_utils.TestCase):

  def test_add_normal_import(self):
    tree = astlib.parse('')
    self.assertEqual(
        'a.b.c',
        import_utils.add_import(tree, 'a.b.c', from_import=False,
                                astlib=astlib))
    self.assertEqual('import a.b.c\n', pasta.dump(tree, astlib=astlib))

  def test_add_normal_import_with_asname(self):
    tree = astlib.parse('')
    self.assertEqual(
        'd',
        import_utils.add_import(
            tree, 'a.b.c', asname='d', from_import=False,
            astlib=astlib))
    self.assertEqual('import a.b.c as d\n', pasta.dump(tree, astlib=astlib))

  def test_add_from_import(self):
    tree = astlib.parse('')
    self.assertEqual(
        'c', import_utils.add_import(tree, 'a.b.c', from_import=True,
                                     astlib=astlib))
    self.assertEqual('from a.b import c\n', pasta.dump(tree, astlib=astlib))

  def test_add_from_import_with_asname(self):
    tree = astlib.parse('')
    self.assertEqual(
        'd',
        import_utils.add_import(
            tree, 'a.b.c', asname='d', from_import=True, astlib=astlib))
    self.assertEqual('from a.b import c as d\n',
                     pasta.dump(tree, astlib=astlib))

  def test_add_single_name_from_import(self):
    tree = astlib.parse('')
    self.assertEqual(
        'foo', import_utils.add_import(tree, 'foo', from_import=True,
                                       astlib=astlib))
    self.assertEqual('import foo\n', pasta.dump(tree, astlib=astlib))

  def test_add_single_name_from_import_with_asname(self):
    tree = astlib.parse('')
    self.assertEqual(
        'bar',
        import_utils.add_import(
            tree, 'foo', asname='bar', from_import=True, astlib=astlib))
    self.assertEqual('import foo as bar\n', pasta.dump(tree, astlib=astlib))

  def test_add_existing_import(self):
    tree = astlib.parse('from a.b import c')
    self.assertEqual('c', import_utils.add_import(tree, 'a.b.c', astlib=astlib))
    self.assertEqual('from a.b import c\n', pasta.dump(tree, astlib=astlib))

  def test_add_existing_import_aliased(self):
    tree = astlib.parse('from a.b import c as d')
    self.assertEqual('d', import_utils.add_import(tree, 'a.b.c', astlib=astlib))
    self.assertEqual('from a.b import c as d\n',
                     pasta.dump(tree, astlib=astlib))

  def test_add_existing_import_aliased_with_asname(self):
    tree = astlib.parse('from a.b import c as d')
    self.assertEqual(
        'd', import_utils.add_import(tree, 'a.b.c', asname='e', astlib=astlib))
    self.assertEqual('from a.b import c as d\n',
                     pasta.dump(tree, astlib=astlib))

  def test_add_existing_import_normal_import(self):
    tree = astlib.parse('import a.b.c')
    self.assertEqual(
        'a.b',
        import_utils.add_import(tree, 'a.b', from_import=False, astlib=astlib))
    self.assertEqual('import a.b.c\n', pasta.dump(tree, astlib=astlib))

  def test_add_existing_import_normal_import_aliased(self):
    tree = astlib.parse('import a.b.c as d')
    self.assertEqual(
        'a.b',
        import_utils.add_import(tree, 'a.b', from_import=False, astlib=astlib))
    self.assertEqual(
        'd',
        import_utils.add_import(tree, 'a.b.c', from_import=False,
                                astlib=astlib))
    self.assertEqual('import a.b\nimport a.b.c as d\n',
                     pasta.dump(tree, astlib=astlib))

  def test_add_import_with_conflict(self):
    tree = astlib.parse('def c(): pass\n')
    self.assertEqual(
        'c_1',
        import_utils.add_import(tree, 'a.b.c', from_import=True, astlib=astlib))
    self.assertEqual('from a.b import c as c_1\ndef c():\n  pass\n',
                     pasta.dump(tree, astlib=astlib))

  def test_add_import_with_asname_with_conflict(self):
    tree = astlib.parse('def c(): pass\n')
    self.assertEqual(
        'c_1',
        import_utils.add_import(
            tree, 'a.b', asname='c', from_import=True, astlib=astlib))
    self.assertEqual('from a import b as c_1\ndef c():\n  pass\n',
                     pasta.dump(tree, astlib=astlib))

  def test_merge_from_import(self):
    tree = astlib.parse('from a.b import c')

    # x is explicitly not merged
    self.assertEqual(
        'x',
        import_utils.add_import(
            tree, 'a.b.x', merge_from_imports=False, astlib=astlib))
    self.assertEqual('from a.b import x\nfrom a.b import c\n',
                     pasta.dump(tree, astlib=astlib))

    # y is allowed to be merged and is grouped into the first matching import
    self.assertEqual(
        'y',
        import_utils.add_import(
            tree, 'a.b.y', merge_from_imports=True, astlib=astlib))
    self.assertEqual('from a.b import x, y\nfrom a.b import c\n',
                     pasta.dump(tree, astlib=astlib))

  def test_add_import_after_docstring(self):
    tree = pasta.parse('\'Docstring.\'\n', astlib=astlib)
    self.assertEqual('a', import_utils.add_import(tree, 'a', astlib=astlib))
    self.assertEqual('\'Docstring.\'\nimport a\n', pasta.dump(tree, astlib=astlib))

class RemoveDuplicatesTest(test_utils.TestCase):

  def test_remove_duplicates(self, astlib=astlib):
    src = """
import a
import b
import c
import b
import d
"""
    tree = astlib.parse(src)
    self.assertTrue(import_utils.remove_duplicates(tree, astlib=astlib))

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
    tree = astlib.parse(src)
    self.assertTrue(import_utils.remove_duplicates(tree, astlib=astlib))

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
    tree = astlib.parse(src)
    self.assertTrue(import_utils.remove_duplicates(tree, astlib=astlib))

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
    tree = astlib.parse(src)
    self.assertFalse(import_utils.remove_duplicates(tree, astlib=astlib))
    self.assertEqual(len(tree.body), 2)

  def test_remove_duplicates_aliases(self):
    src = """
import a
import a as ax
import a as ax2
import a as ax
"""
    tree = astlib.parse(src)
    self.assertTrue(import_utils.remove_duplicates(tree, astlib=astlib))
    self.assertEqual(len(tree.body), 3)
    self.assertEqual(tree.body[0].names[0].asname, None)
    self.assertEqual(tree.body[1].names[0].asname, 'ax')
    self.assertEqual(tree.body[2].names[0].asname, 'ax2')


if __name__ == '__main__':
  unittest.main()
