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

import copy

from pasta.augment import errors


# TODO smithnick: Add docstring, handle bad inputs and error conditions
def split_import(sc, node, alias_to_remove):
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
