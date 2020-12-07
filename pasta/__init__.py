# coding=utf-8
"""Pasta enables AST-based transformations on python source code."""
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

import sys

from pasta.base import annotate
from pasta.base import ast_utils
from pasta.base import codegen
from typed_ast import ast27
from typed_ast import ast3
from typing import Iterable
from typing import Tuple
from typing import Union


def ast_parse(
    source: str,
    py_ver: Tuple[int,
                  int] = sys.version_info[:2]) -> Union[ast27.AST, ast3.AST]:
  if py_ver < (3, 0):
    return ast27.parse(source)
  else:
    return ast3.parse(source)


def ast_walk(
    tree: Union[ast27.AST, ast3.AST],
    py_ver: Tuple[int, int] = sys.version_info[:2]
) -> Iterable[Union[ast27.AST, ast3.AST]]:
  if py_ver < (3, 0):
    return ast27.walk(tree)
  else:
    return ast3.walk(tree)


def parse(src: str, py_ver: Tuple[int, int] = sys.version_info[:2]):
  t = ast_utils.parse(src, py_ver)
  annotator = annotate.get_ast_annotator(py_ver)(src)
  annotator.visit(t)
  return t


def dump(tree: Union[ast27.AST, ast3.AST],
         py_ver: Tuple[int, int] = sys.version_info[:2]):
  return codegen.to_str(tree, py_ver)
