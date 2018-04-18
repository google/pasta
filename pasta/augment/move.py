"""TODO(smithnick): DO NOT SUBMIT without one-line documentation for move.

TODO(smithnick): DO NOT SUBMIT without a detailed description of move.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


def extract_node(tree, node, module_name):
  if node not in tree.body:
    raise NotImplemented

  sc = scope.analyze(tree)
  node_sc = sc.get_scope_for_node(node)
  tree.body.remove(node)

  if not node_sc:
    return node, {}

  def is_child_node(n):
    v = ast_utils.FindNodeVisitor(lambda n2: n == n2)
    v.visit(node)
    return bool(v.results)

  deps = {}
  for external_name in sc.names:
    if any(is_child_node(read_node) for read_node in external_name.reads):
      if isinstance(external_name.definition, ast.Import):
        deps[external_name.id] = external_name.definition
