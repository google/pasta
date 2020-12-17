"""Tests for google3.third_party.py.pasta.pasta."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from typed_ast import ast27
from typed_ast import ast3
from typing import Union
import unittest

import google3
from pasta.augment import import_utils_test
from pasta.augment import rename_test
from pasta.base import annotate_test
from pasta.base import codegen_test
from pasta.base import scope_test

from google3.testing.pybase import googletest

class PastaTestCase(googletest.TestCase):

  def run_test_suite(self, suite):
    self.assertGreater(suite.countTestCases(), 0, 'Test suite is empty.')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    self.assertTrue(result.wasSuccessful())

class PastaBaseTest(PastaTestCase):

  def test_ast_utils(self):
    self.run_test_suite(ast_utils_test.suite((3, 8)))
    self.run_test_suite(ast_utils_test.suite((2, 7)))

  def test_annotate(self):
    self.run_test_suite(annotate_test.suite((3, 8)))
    self.run_test_suite(annotate_test.suite((2, 7)))

  def test_scope(self):
    self.run_test_suite(scope_test.suite((3, 8)))
    self.run_test_suite(scope_test.suite((2, 7)))

  def test_codegen(self):
    self.run_test_suite(codegen_test.suite((3, 8)))
    self.run_test_suite(codegen_test.suite((2, 7)))


class PastaAugmentTest(PastaTestCase):

  def test_import_utils(self):
    self.run_test_suite(import_utils_test.suite((3, 8)))
    self.run_test_suite(import_utils_test.suite((2, 7)))

  def test_rename(self):
    self.run_test_suite(rename_test.suite((3, 8)))
    self.run_test_suite(rename_test.suite((2, 7)))


if __name__ == '__main__':
  googletest.main()
