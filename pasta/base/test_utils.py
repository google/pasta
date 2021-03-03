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

import ast
import sys
import unittest

from six.moves import zip

import pasta


class TestCase(unittest.TestCase):

  def checkAstsEqual(self, a, b, astlib=ast):
    """Compares two ASTs and fails if there are differences.

    Ignores `ctx` fields and formatting info.
    """
    if a is None and b is None:
      return
    try:
      self.assertIsNotNone(a)
      self.assertIsNotNone(b)
      for node_a, node_b in zip(astlib.walk(a), astlib.walk(b)):
        self.assertEqual(type(node_a), type(node_b))
        for field in type(node_a)()._fields:
          a_val = getattr(node_a, field, None)
          b_val = getattr(node_b, field, None)

          if isinstance(a_val, list):
            for item_a, item_b in zip(a_val, b_val):
              self.checkAstsEqual(item_a, item_b, astlib)
          elif isinstance(a_val, astlib.AST) or isinstance(
              b_val, astlib.AST):
            if (not isinstance(a_val,
                               (astlib.Load, astlib.Store, astlib.Param)) and
                not isinstance(b_val,
                               (astlib.Load, astlib.Store, astlib.Param))):
              self.assertIsNotNone(a_val)
              self.assertIsNotNone(b_val)
              self.checkAstsEqual(a_val, b_val, astlib)
          else:
            self.assertEqual(a_val, b_val)
    except AssertionError as ae:
      self.fail('ASTs differ:\n%s\n  !=\n%s\n\n' %
                (astlib.dump(a), astlib.dump(b)))


if not hasattr(TestCase, 'assertItemsEqual'):
  setattr(TestCase, 'assertItemsEqual', TestCase.assertCountEqual)


def requires_features(features, astlib=ast):
  return unittest.skipIf(
      any(not supports_feature(feature, astlib) for feature in features),
      ('Tests features which are not supported by this version of python %s. ' %
       (astlib,)) +
      ('Missing: %r' %
       ([f for f in features if not supports_feature(f, astlib)])))


def supports_feature(feature, astlib=ast):
  if feature == 'bytes_node':
    return hasattr(astlib, 'Bytes') and issubclass(astlib.Bytes, astlib.AST)
  if feature == 'exec_node':
    return hasattr(astlib, 'Exec') and issubclass(astlib.Exec, astlib.AST)
  if feature == 'type_annotations':
    return _try_to_parse('def foo(bar: str=123) -> None: pass', astlib)
  if feature == 'fstring':
    return hasattr(astlib, 'JoinedStr') and issubclass(astlib.JoinedStr, astlib.AST)
  # Python 2 counts tabs as 8 spaces for indentation
  if feature == 'mixed_tabs_spaces':
    return _try_to_parse('def a():	b\n       c', astlib)
  if feature == 'ur_str_literal':
    return _try_to_parse('ur""', astlib)
  return False


def _try_to_parse(src, astlib):
  try:
    astlib.parse(src)
  except SyntaxError:
    return False
  return True
