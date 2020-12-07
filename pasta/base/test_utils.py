# coding=utf-8
"""Useful stuff for tests."""
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

#import ast
import sys
from typed_ast import ast27
from typed_ast import ast3
from typing import List
from typing import Tuple
from typing import Union
import unittest

from six.moves import zip

import pasta


class TestCase(unittest.TestCase):

  def checkAstsEqual(self, a, b, py_ver: Tuple[int, int]):
    """Compares two ASTs and fails if there are differences.

    Ignores `ctx` fields and formatting info.
    """
    if a is None and b is None:
      return
    try:
      self.assertIsNotNone(a)
      self.assertIsNotNone(b)
      for node_a, node_b in zip(
          pasta.ast_walk(a, py_ver), pasta.ast_walk(b, py_ver)):
        self.assertEqual(type(node_a), type(node_b))
        for field in type(node_a)()._fields:
          a_val = getattr(node_a, field, None)
          b_val = getattr(node_b, field, None)

          if isinstance(a_val, list):
            for item_a, item_b in zip(a_val, b_val):
              self.checkAstsEqual(item_a, item_b, py_ver)
          elif isinstance(a_val, (ast27.AST, ast3.AST)) or isinstance(
              b_val, (ast27.AST, ast3.AST)):
            if (not isinstance(a_val, (ast27.Load, ast3.Load, ast27.Store,
                                       ast3.Store, ast27.Param, ast3.Param)) and
                not isinstance(b_val, (ast27.Load, ast3.Load, ast27.Store,
                                       ast3.Store, ast27.Param, ast3.Param))):
              self.assertIsNotNone(a_val)
              self.assertIsNotNone(b_val)
              self.checkAstsEqual(a_val, b_val, py_ver)
          else:
            self.assertEqual(a_val, b_val)
    except AssertionError as ae:
      self.fail('ASTs differ:\n%s\n  !=\n%s\n\n%s' %
                (ast27.dump(a) if py_ver <
                 (3, 0) else ast3.dump(a), ast27.dump(b) if py_ver <
                 (3, 0) else ast3.dump(b), ae))


if not hasattr(TestCase, 'assertItemsEqual'):
  setattr(TestCase, 'assertItemsEqual', TestCase.assertCountEqual)


def requires_features(features: List[str], py_ver: Tuple[int, int]) -> bool:
  return unittest.skipIf(
      any(not supports_feature(feature, py_ver) for feature in features),
      ('Tests features which are not supported by this version of python %s. ' %
       (py_ver,)) +
      ('Missing: %r' %
       ([f for f in features if not supports_feature(f, py_ver)])))


def supports_feature(feature: str, py_ver: Tuple[int, int]) -> bool:
  if feature == 'ur_str_literal':
    return py_ver < (3, 0)
  if feature == 'bytes_node':
    return py_ver >= (3, 0)
  if feature == 'exec_node':
    return py_ver < (3, 0)
  if feature == 'type_annotations':
    return py_ver >= (3, 0)
  if feature == 'fstring':
    return py_ver >= (3, 0)
  # Python 2 counts tabs as 8 spaces for indentation
  if feature == 'mixed_tabs_spaces':
    return py_ver < (3, 0)
  return False
