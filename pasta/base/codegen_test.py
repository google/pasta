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

import os.path
import unittest
from six import with_metaclass
from typed_ast import ast27
from typed_ast import ast3

import pasta
from pasta.base import codegen
from pasta.base import test_utils
from pasta import pasta_test

TESTDATA_DIR = os.path.realpath(
    os.path.join(os.path.dirname(pasta.__file__), '../testdata'))


def suite(py_ver):

  def _is_syntax_valid(filepath, py_ver):
    with open(filepath, 'r') as f:
      try:
        t = pasta.ast_parse(f.read(), py_ver)
      except SyntaxError:
        return False
    return True

  class AutoFormatTestMeta(type):

    def __new__(mcs, name, bases, inst_dict):
      # Helper function to generate a test method
      def auto_format_test_generator(input_file):

        def test(self):
          with open(input_file, 'r') as handle:
            src = handle.read()
          t = pasta.ast_parse(src, py_ver)
          auto_formatted = pasta.dump(t, py_ver)
          self.assertMultiLineEqual(src, auto_formatted)

        return test

      # Add a test method for each input file
      test_method_prefix = 'test_auto_format_'
      data_dir = os.path.join(TESTDATA_DIR, 'codegen')
      for dirpath, _, files in os.walk(data_dir):
        for filename in files:
          if filename.endswith('.in'):
            full_path = os.path.join(dirpath, filename)
            inst_dict[test_method_prefix + filename[:-3]] = unittest.skipIf(
                not _is_syntax_valid(full_path),
                'Test contains syntax not supported by this version.',
            )(
                auto_format_test_generator(full_path))
      return type.__new__(mcs, name, bases, inst_dict)

  class AutoFormatTest(with_metaclass(AutoFormatTestMeta, test_utils.TestCase)):
    """Tests that code without formatting info is printed neatly."""

    def test_imports(self):
      src = 'from a import b\nimport c, d\nfrom ..e import f, g\n'
      t = pasta.ast_parse(src, py_ver)
      self.assertEqual(src, pasta.dump(t, py_ver))

    @test_utils.requires_features(['exec_node'], py_ver)
    def test_exec_node_default(self):
      src = 'exec foo in bar'
      t = pasta.ast_parse(src, py_ver)
      self.assertEqual('exec(foo, bar)\n', pasta.dump(t, py_ver))

    @test_utils.requires_features(['bytes_node'], py_ver)
    def test_bytes(self):
      src = "b'foo'"
      t = pasta.ast_parse(src, py_ver)
      self.assertEqual("b'foo'\n", pasta.dump(t, py_ver))

    def test_unicode_str(self):
      src = "u'foo'"
      t = pasta.parse(src, py_ver)
      self.assertEqual("u'foo'", pasta.dump(t, py_ver))

    @test_utils.requires_features(['ur_str_literal'], py_ver)
    def test_unicode_raw_str(self):
      src = "ur'foo'"
      t = pasta.parse(src, py_ver)
      self.assertEqual("ur'foo'", pasta.dump(t, py_ver))

    @test_utils.requires_features(['bytes_node'], py_ver)
    def test_args(self):
      src = """
def func():
  offset_multi = lambda *a: foo(*a)
  add_multi = lambda *a, **k: bar(*a, **k)"""
      t = pasta.parse(src, py_ver)
      print(pasta.dump(t, py_ver))
      self.assertEqual(src, pasta.dump(t, py_ver))

    def test_default_indentation(self):
      for indent in ('  ', '    ', '\t'):
        src = 'def a():\n' + indent + 'b\n'
        t = pasta.parse(src, py_ver)
        t.body.extend(pasta.ast_parse('def c(): d', py_ver).body)
        self.assertEqual(pasta.dump(t, py_ver), src + 'def c():\n' + indent + 'd\n')

    def test_globals_where_first_ident_reoccurs(self):
      src = 'global a, b, a'
      t = pasta.parse(src, py_ver)
      self.assertEqual('global a, b, a', pasta.dump(t, py_ver))

    def test_compare_where_separator_whitespace_deleted(self):
      src = "if a     in      b:\n  pass"
      t = pasta.parse(src, py_ver)
      t.body[0].test.left.__pasta__['suffix'] = ''
      t.body[0].test.__pasta__['op_suffix_0'] = ''
      self.assertEqual("if a in b:\n  pass", pasta.dump(t, py_ver))

    def test_except_where_separator_whitespace_deleted(self):
      src = "try:\n  pass\nexcept Type      as    var:\n  pass"
      t = pasta.parse(src, py_ver)
      t.body[0].handlers[0].type.__pasta__['suffix'] = ''
      self.assertEqual("try:\n  pass\nexcept Type as    var:\n  pass", pasta.dump(t, py_ver))


  result = unittest.TestSuite()
  result.addTests(unittest.makeSuite(AutoFormatTest))
  return result


if __name__ == '__main__':
  unittest.main()
