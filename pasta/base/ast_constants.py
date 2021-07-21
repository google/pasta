"""Constants relevant to ast code."""
# Copyright 2021 Google LLC
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

def get_node_type_to_tokens(astlib):
  result = {
      astlib.Add: ('+',),
      astlib.And: ('and',),
      astlib.BitAnd: ('&',),
      astlib.BitOr: ('|',),
      astlib.BitXor: ('^',),
      astlib.Div: ('/',),
      astlib.Eq: ('==',),
      astlib.FloorDiv: ('//',),
      astlib.Gt: ('>',),
      astlib.GtE: ('>=',),
      astlib.In: ('in',),
      astlib.Invert: ('~',),
      astlib.Is: ('is',),
      astlib.IsNot: (
          'is',
          'not',
      ),
      astlib.LShift: ('<<',),
      astlib.Lt: ('<',),
      astlib.LtE: ('<=',),
      astlib.Mod: ('%',),
      astlib.Mult: ('*',),
      astlib.Not: ('not',),
      astlib.NotEq: ('!=',),
      astlib.NotIn: (
          'not',
          'in',
      ),
      astlib.Or: ('or',),
      astlib.Pow: ('**',),
      astlib.RShift: ('>>',),
      astlib.Sub: ('-',),
      astlib.UAdd: ('+',),
      astlib.USub: ('-',),
  }
  if hasattr(astlib, 'MatMult'):
    result[astlib.MatMult] = ('@',)
  return result
