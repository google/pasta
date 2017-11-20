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
import unittest


class TestCase(unittest.TestCase):
  pass


if not hasattr(TestCase, 'assertMultiLineEqual'):
  def assertMultiLineEqual(self, before, after):
    self.assertEqual(before, after, 'Output does not match expected\n' +
                     '\n'.join(get_diff(before, after)))
  setattr(TestCase, 'assertMultiLineEqual', assertMultiLineEqual)


if not hasattr(TestCase, 'assertItemsEqual'):
  setattr(TestCase, 'assertItemsEqual', TestCase.assertCountEqual)


def requires_features(*features):
  return unittest.skipIf(
      any(not supports_feature(feature) for feature in features),
      'Tests features which are not supported by this version of python. '
      'Missing: %r' % [f for f in features if not supports_feature(f)])


def supports_feature(feature):
  if feature == 'type_annotations':
    try:
      ast.parse('def foo(bar: str=123) -> None: pass')
    except SyntaxError:
      return False
    return True
  return False
