# coding=utf-8
"""Tests for annotate."""
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
import difflib
import os.path
from six import with_metaclass
import sys
import textwrap
import unittest

import pasta
from pasta.base import annotate
from pasta.base import ast_utils
from pasta.base import codegen
from pasta.base import test_utils

TESTDATA_DIR = os.path.realpath(
    os.path.join(os.path.dirname(pasta.__file__), '../testdata'))


class PrefixSuffixTest(test_utils.TestCase):

  def test_block_suffix(self):
    src_tpl = textwrap.dedent('''\
        {open_block}
          pass #a
          #b
            #c

          #d
        #e
        a
        ''')
    test_cases = (
        'def x():',
        'class X:',
        'if x:',
        'if x:\n  y\nelse:',
        'if x:\n  y\nelif y:',
        'while x:',
        'while x:\n  y\nelse:',
        'try:\n  x\nfinally:',
        'try:\n  x\nexcept:',
        'try:\n  x\nexcept:\n  y\nelse:',
        'with x:',
        'with x, y:',
        'with x:\n with y:',
        'for x in y:',
    )
    def is_node_for_suffix(node):
      # Return True if this node contains the 'pass' statement
      for attr in dir(node):
        attr_val = getattr(node, attr)
        if (isinstance(attr_val, list) and
            any(isinstance(child, ast.Pass) for child in attr_val)):
          return True
      return False
    node_finder = ast_utils.FindNodeVisitor(is_node_for_suffix)

    for open_block in test_cases:
      src = src_tpl.format(open_block=open_block)
      t = pasta.parse(src)
      node_finder.results = []
      node_finder.visit(t)
      node = node_finder.results[0]
      expected = '  #b\n    #c\n\n  #d\n'
      actual = ast_utils.prop(node, 'suffix')
      self.assertMultiLineEqual(
          expected, actual,
          'Incorrect suffix for code:\n%s\nNode: %s (line %d)\nDiff:\n%s' % (
              src, node, node.lineno, '\n'.join(_get_diff(actual, expected))))

  def test_module_suffix(self):
    src = 'foo\n#bar\n\n#baz\n'
    t = pasta.parse(src)
    self.assertEquals(src[src.index('#bar'):], ast_utils.prop(t, 'suffix'))

  def test_no_block_suffix_for_single_line_statement(self):
    src = 'if x:  return y\n  #a\n#b\n'
    t = pasta.parse(src)
    self.assertEqual('', ast_utils.prop(t.body[0], 'suffix'))

  def test_expression_prefix_suffix(self):
    src = 'a\n\nfoo\n\n\nb\n'
    t = pasta.parse(src)
    self.assertEqual('\n', ast_utils.prop(t.body[1], 'prefix'))
    self.assertEqual('\n', ast_utils.prop(t.body[1], 'suffix'))

  def test_statement_prefix_suffix(self):
    src = 'a\n\ndef foo():\n  return bar\n\n\nb\n'
    t = pasta.parse(src)
    self.assertEqual('\n', ast_utils.prop(t.body[1], 'prefix'))
    self.assertEqual('', ast_utils.prop(t.body[1], 'suffix'))

  def test_scope_trailing_comma(self):
    template = 'def foo(a, b{trailing_comma}): pass'
    for trailing_comma in ('', ',', ' , '):
      tree = pasta.parse(template.format(trailing_comma=trailing_comma))
      self.assertEqual(trailing_comma.lstrip(' ') + ')',
                       ast_utils.prop(tree.body[0], 'args_suffix'))

    template = 'class Foo(a, b{trailing_comma}): pass'
    for trailing_comma in ('', ',', ' , '):
      tree = pasta.parse(template.format(trailing_comma=trailing_comma))
      self.assertEqual(trailing_comma.lstrip(' ') + ')',
                       ast_utils.prop(tree.body[0], 'bases_suffix'))

    template = 'from mod import (a, b{trailing_comma})'
    for trailing_comma in ('', ',', ' , '):
      tree = pasta.parse(template.format(trailing_comma=trailing_comma))
      self.assertEqual(trailing_comma + ')',
                       ast_utils.prop(tree.body[0], 'names_suffix'))


def _is_syntax_valid(filepath):
  with open(filepath, 'r') as f:
    try:
      ast.parse(f.read())
    except SyntaxError:
      return False
  return True


class SymmetricTestMeta(type):

  def __new__(mcs, name, bases, inst_dict):
    # Helper function to generate a test method
    def symmetric_test_generator(filepath):
      def test(self):
        with open(filepath, 'r') as handle:
          src = handle.read()
        t = ast_utils.parse(src)
        annotator = annotate.AstAnnotator(src)
        annotator.visit(t)
        self.assertMultiLineEqual(codegen.to_str(t), src)
        self.assertEqual([], annotator.tokens._parens, 'Unmatched parens')
      return test

    # Add a test method for each input file
    test_method_prefix = 'test_symmetric_'
    data_dir = os.path.join(TESTDATA_DIR, 'ast')
    for dirpath, dirs, files in os.walk(data_dir):
      for filename in files:
        if filename.endswith('.in'):
          full_path = os.path.join(dirpath, filename)
          inst_dict[test_method_prefix + filename[:-3]] = unittest.skipIf(
                    not _is_syntax_valid(full_path),
                    'Test contains syntax not supported by this version.',
                  )(symmetric_test_generator(full_path))
    return type.__new__(mcs, name, bases, inst_dict)


class SymmetricTest(with_metaclass(SymmetricTestMeta, test_utils.TestCase)):
  """Validates the symmetry property.

  After parsing + annotating a module, regenerating the source code for it
  should yield the same result.
  """


def _get_node_identifier(node):
  for attr in ('id', 'name', 'attr', 'arg', 'module'):
    if isinstance(getattr(node, attr, None), str):
      return getattr(node, attr, '')
  return ''


class PrefixSuffixGoldenTestMeta(type):

  def __new__(mcs, name, bases, inst_dict):
    # Helper function to generate a test method
    def golden_test_generator(input_file, golden_file):
      def test(self):
        with open(input_file, 'r') as handle:
          src = handle.read()
        t = ast_utils.parse(src)
        annotator = annotate.AstAnnotator(src)
        annotator.visit(t)

        def escape(s):
          return '' if s is None else s.replace('\n', '\\n')

        result = '\n'.join(
            "{0:12} {1:20} \tprefix=|{2}|\tsuffix=|{3}|".format(
                str((getattr(n, 'lineno', -1), getattr(n, 'col_offset', -1))),
                type(n).__name__ + ' ' + _get_node_identifier(n),
                escape(ast_utils.prop(n, 'prefix')),
                escape(ast_utils.prop(n, 'suffix')))
            for n in ast.walk(t)) + '\n'

        # If specified, write the golden data instead of checking it
        if getattr(self, 'generate_goldens', False):
          if not os.path.isdir(os.path.dirname(golden_file)):
            os.makedirs(os.path.dirname(golden_file))
          with open(golden_file, 'w') as f:
            f.write(result)
          print('Wrote: ' + golden_file)
          return

        try:
          with open(golden_file, 'r') as f:
            golden = f.read()
        except IOError:
          self.fail('Missing golden data.')

        self.assertMultiLineEqual(golden, result)
      return test

    # Add a test method for each input file
    test_method_prefix = 'test_golden_prefix_suffix_'
    data_dir = os.path.join(TESTDATA_DIR, 'ast')
    python_version = '%d.%d' % sys.version_info[:2]
    for dirpath, dirs, files in os.walk(data_dir):
      for filename in files:
        if filename.endswith('.in'):
          full_path = os.path.join(dirpath, filename)
          golden_path = os.path.join(dirpath, 'golden', python_version,
                                     filename[:-3] + '.out')
          inst_dict[test_method_prefix + filename[:-3]] = unittest.skipIf(
                    not _is_syntax_valid(full_path),
                    'Test contains syntax not supported by this version.',
                  )(golden_test_generator(full_path, golden_path))
    return type.__new__(mcs, name, bases, inst_dict)


class PrefixSuffixGoldenTest(with_metaclass(PrefixSuffixGoldenTestMeta,
                                            test_utils.TestCase)):
  """Checks the prefix and suffix on each node in the AST.

  This uses golden files in testdata/ast/golden. To regenerate these files, run
  python setup.py test -s pasta.base.annotate_test.generate_goldens
  """

  maxDiff = None


def _get_diff(before, after):
  return difflib.ndiff(after.splitlines(), before.splitlines())


def suite():
  result = unittest.TestSuite()
  result.addTests(unittest.makeSuite(SymmetricTest))
  result.addTests(unittest.makeSuite(PrefixSuffixTest))
  result.addTests(unittest.makeSuite(PrefixSuffixGoldenTest))
  return result


def generate_goldens():
  result = unittest.TestSuite()
  result.addTests(unittest.makeSuite(PrefixSuffixGoldenTest))
  setattr(PrefixSuffixGoldenTest, 'generate_goldens', True)
  return result


if __name__ == '__main__':
  unittest.main()
