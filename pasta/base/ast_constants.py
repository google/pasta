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

import ast

NODE_TYPE_TO_TOKENS = {
    ast.Add: ('+',),
    ast.And: ('and',),
    ast.BitAnd: ('&',),
    ast.BitOr: ('|',),
    ast.BitXor: ('^',),
    ast.Div: ('/',),
    ast.Eq: ('==',),
    ast.FloorDiv: ('//',),
    ast.Gt: ('>',),
    ast.GtE: ('>=',),
    ast.In: ('in',),
    ast.Invert: ('~',),
    ast.Is: ('is',),
    ast.IsNot: ('is', 'not',),
    ast.LShift: ('<<',),
    ast.Lt: ('<',),
    ast.LtE: ('<=',),
    ast.Mod: ('%',),
    ast.Mult: ('*',),
    ast.Not: ('not',),
    ast.NotEq: ('!=',),
    ast.NotIn: ('not', 'in',),
    ast.Or: ('or',),
    ast.Pow: ('**',),
    ast.RShift: ('>>',),
    ast.Sub: ('-',),
    ast.UAdd: ('+',),
    ast.USub: ('-',),
}


if hasattr(ast, 'MatMult'):
  NODE_TYPE_TO_TOKENS[ast.MatMult] = ('@',)
