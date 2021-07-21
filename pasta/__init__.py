# coding=utf-8
"""Pasta enables AST-based transformations on python source code."""
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
import sys

from pasta.base import annotate
from pasta.base import ast_utils
from pasta.base import codegen


def parse(src, astlib=ast):
  t = ast_utils.parse(src, astlib)
  annotator = annotate.get_ast_annotator(astlib)(src)
  annotator.visit(t)
  return t


def dump(tree, astlib=ast):
  return codegen.to_str(tree, astlib)
