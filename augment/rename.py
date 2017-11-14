# coding=utf-8
"""Rename names in a python module."""
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
import copy
import itertools

from augment import import_utils
import scope


def rename_external(t, old_name, new_name):
  sc = scope.analyze(t)

  if old_name not in sc.external_references:
    return False

  already_changed = []
  for node in sc.external_references[old_name]:
    if isinstance(node, ast.alias):
      parent = sc.parent(node)
      if isinstance(parent, ast.ImportFrom):
        if parent not in already_changed:
          assert _rename_name_in_importfrom(sc, parent, old_name, new_name)
          already_changed.append(parent)
      elif isinstance(parent, ast.Import):
        node.name = new_name + node.name[len(old_name):]
    elif isinstance(node, ast.ImportFrom):
      if node not in already_changed:
        assert _rename_name_in_importfrom(sc, node, old_name, new_name)
        already_changed.append(node)

  return True


def _rename_name_in_importfrom(sc, node, old_name, new_name):
  if old_name == new_name:
    return False

  module_parts = node.module.split('.')
  old_parts = old_name.split('.')
  new_parts = new_name.split('.')

  # If just the module is changing, rename it
  if module_parts[:len(old_parts)] == old_parts:
    node.module = '.'.join(new_parts + module_parts[len(old_parts):])
    return True
    
  # Find the alias node to be changed
  for alias_to_change in node.names:
    if alias_to_change.name == old_parts[-1]:
      break
  else:
    return False

  alias_to_change.name = new_parts[-1]

  # Split the import if the package has changed
  if module_parts != new_parts[:-1]:
    if len(node.names) > 1:
      new_import = import_utils.split_import(sc, node, alias_to_change)
      new_import.module = '.'.join(new_parts[:-1])
    else:
      node.module = '.'.join(new_parts[:-1])

  return True
