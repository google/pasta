"""TODO(smithnick): DO NOT SUBMIT without one-line documentation for extract.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import ast

from pasta.augment import import_utils
from pasta.base import ast_utils
from pasta.base import scope


def extract_node(tree, node, src_module_name, remove_node=True,
                 cleanup_imports=True):
  """Extract a node from an AST.

  Arguments:
    tree: (ast.AST) Tree containing the node to be removed.
    node: (ast.AST) Node to remove.
    src_module_name: (string) Absolute name of the module the node is being
      extracted from.
    remove_node: (boolean) If True, remove the node from the AST.
    cleanup_imports: (boolean) If True, remove imports that were previously only
      used in the removed node.

  Returns:
    Dictionary mapping from names referenced in the removed node scope to the
    absolute path for that name.
  """
  sc = scope.analyze(tree)
  references = {}

  for name in sc.names.values():
    if not name.definition:
      continue
    refs_under_node = {ref for ref in name.reads
                       if ast_utils.find_nodes(node, lambda n: n is ref)}
    if not refs_under_node:
      continue

    def_parent = sc.parent(name.definition)
    if isinstance(def_parent, (ast.Import, ast.ImportFrom)):
      # TODO: Support relative imports
      import_name = (name.definition.name if isinstance(def_parent, ast.Import)
                     else '.'.join((def_parent.module, name.definition.name)))
      references[name.id] = import_name

      if cleanup_imports and len(name.reads) == len(refs_under_node):
        import_utils.remove_import_alias_node(sc, name.definition)
    else:
      references[name.id] = '.'.join((src_module_name, name.id))

  ast_utils.remove_child(sc.parent(node), node)
  return references


def insert_node(tree, node, references, use_from_imports=True):
  """Insert a node into a tree with external references."""
  sc = scope.analyze(node)
  for name in sc.names.values():
    if name.definition is None and name.id in references:
      asname = import_utils.add_import(tree, references[name.id],
                                       from_import=use_from_imports)
      for read in name.reads:
        ast_utils.replace_child(sc.parent(read), read, _name_to_node(asname))
  tree.body.append(node)


def _name_to_node(name):
  name_parts = name.split('.')
  node = ast.Name(id=name_parts[0])
  for part in name_parts[1:]:
    node = ast.Attribute(value=node, attr=part)
  return node
