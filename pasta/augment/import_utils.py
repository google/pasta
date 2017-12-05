# coding=utf-8
"""Functions for dealing with import statements."""
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

from pasta.augment import errors
from pasta.base import scope


def split_import(sc, node, alias_to_remove):
  """Split an import node by moving the given imported alias into a new import.

  Arguments:
    sc: (scope.Scope) Scope computed on whole tree of the code being modified.
    node: (ast.Import|ast.ImportFrom) An import node to split.
    alias_to_remove: (ast.alias) The import alias node to remove. This must be a
      child of the given `node` argument.

  Raises:
    errors.InvalidAstError: if `node` is not appropriately contained in the tree
      represented by the scope `sc`.
  """
  parent = sc.parent(node)
  parent_list = None
  for a in ('body', 'orelse', 'finalbody'):
    if hasattr(parent, a) and node in getattr(parent, a):
      parent_list = getattr(parent, a)
      break
  else:
    raise errors.InvalidAstError('Unable to find list containing import %r on '
                                 'parent node %r' % (node, parent))

  idx = parent_list.index(node)
  new_import = copy.deepcopy(node)
  new_import.names = [alias_to_remove]
  node.names.remove(alias_to_remove)

  parent_list.insert(idx + 1, new_import)
  return new_import

def get_unused_imports(tree):
  """Get the import nodes that aren't used.

  Arguments:
    tree: (ast.AST) An ast tree to find imports in.

  Returns:
    A list of ast.AST representing nodes that are imports or parts of imports
    (aliases) that can be removed because they are unused.
  """
  sc = scope.analyze(tree)
  unused_aliases = set()
  for node in ast.walk(tree):
    if isinstance(node, ast.alias):
      name = sc.lookup_name(
          node.asname if node.asname is not None else node.name)
      if not name.reads:
        unused_aliases.add(node)

  unused_imports = []
  for node in ast.walk(tree):
    if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
      for alias in node.names:
        if alias in unused_aliases:
          if len(node.names) == 1:
            unused_imports.append(node)
          else:
            unused_imports.append(alias)

  return unused_imports
