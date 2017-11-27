# coding=utf-8
"""Token generator for analyzing source code in logical units.

This module contains the TokenGenerator used for annotating a parsed syntax tree
with source code formatting.
"""
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
import contextlib
import itertools
import tokenize
from six import StringIO

from pasta.base import ast_utils

# Alias for extracting token names
TOKENS = tokenize


class TokenGenerator(object):

  def __init__(self, source):
    self._tokens = list(
        tokenize.generate_tokens(StringIO(source).readline))
    self._parens = []
    self._hints = 0
    self._scope_stack = []
    self._lines = source.splitlines(True)
    self._len = len(self._tokens)
    self._i = -1
    self._eaten = -1
    self._loc = self.loc_begin()

  def loc_begin(self):
    """Get the start column of the current location parsed to."""
    if self._i < 0:
      return (1, 0)
    return self._tokens[self._i][2]

  def loc_end(self):
    """Get the end column of the current location parsed to."""
    if self._i < 0:
      return (1, 0)
    return self._tokens[self._i][3]

  def peek(self):
    """Get the next token without advancing."""
    if self._i >= self._len:
      return None
    return self._tokens[self._i + 1]

  def next(self, advance=True):
    """Consume the next token and optionally advance the current location."""
    self._i += 1
    if self._i >= self._len:
      return None
    if advance:
      self._loc = self._tokens[self._i][3]
    return self._tokens[self._i]

  def rewind(self, amount=1):
    """Rewind the token iterator."""
    self._i -= amount

  def whitespace(self, oneline=False):
    """Parses whitespace from the current _loc to the next non-whitespace.

    Pre-condition:
      `_loc' represents the point before which everything has been parsed and
      after which nothing has been parsed.
    Post-condition:
      `_loc' is exactly at the character that was parsed to.
    """
    def predicate(token):
      return (token[0] in (TOKENS.COMMENT, TOKENS.INDENT, TOKENS.DEDENT) or
              not oneline and token[0] in (TOKENS.NL, TOKENS.NEWLINE))
    whitespace = list(self.takewhile(predicate, advance=False))
    next_token = self.peek()

    result = ''
    for tok in itertools.chain(whitespace, (next_token,)):
      result += self._space_between(self._loc, tok)
      if tok != next_token:
        result += tok[1]
        self._loc = tok[3]
      else:
        self._loc = tok[2]

    # Eat a single newline character
    if next_token[0] in (TOKENS.NL, TOKENS.NEWLINE):
      result += self.next()[1]

    return result

  def open_scope(self, node):
    """Open a parenthesized scope on the given node."""
    prev_loc = self._loc

    def predicate(token):
      return (token[0] in (TOKENS.NL, TOKENS.NEWLINE, TOKENS.COMMENT,
                           TOKENS.INDENT) or token[1] in '(')
    whitespace = list(self.takewhile(predicate, advance=False))
    next_token = self.next(advance=False)

    result = ''
    parens = []
    last_paren_loc = None
    for tok in whitespace:
      result += self._space_between(prev_loc, tok)
      result += tok[1]
      prev_loc = tok[3]

      if tok[1] == '(':
        last_paren_loc = prev_loc
        parens.append(result)
        result = ''

    if parens:
      parens[-1] += self._space_between(last_paren_loc, next_token)

      for paren in parens:
        self._parens.append(paren)
        self._scope_stack.append(_scope_helper(node))
      self._loc = next_token[2]
      self.rewind(1)
    else:
      self.rewind(len(whitespace) + 1)

  def close_scope(self, node):
    """Close a parenthesized scope on the given node, if one is open."""
    if not self._parens:
      return
    prev_loc = self._loc

    def predicate(token):
      return (token[0] in (TOKENS.NL, TOKENS.NEWLINE, TOKENS.COMMENT,
                           TOKENS.INDENT, TOKENS.DEDENT) or token[1] in ')')
    whitespace = list(self.takewhile(predicate, advance=False))

    count = 0
    result = ''
    for tok in whitespace:
      count += 1
      if not self._parens or node not in self._scope_stack[-1]:
        continue

      result += self._space_between(prev_loc, tok)
      result += tok[1]
      prev_loc = tok[3]

      if tok[1] == ')':
        self._scope_stack.pop()
        ast_utils.prependprop(node, 'prefix', self._parens.pop())
        ast_utils.appendprop(node, 'suffix', result)
        result = ''
        count = 0
        self._loc = tok[3]
    self.rewind(count)

  def hint_open(self):
    """Indicates opening a group of parentheses or brackets."""
    self._hints += 1

  def hint_closed(self):
    """Indicates closing a group of parentheses or brackets."""
    self._hints -= 1
    if self._hints < 0:
      raise ValueError('Hint value negative')

  @contextlib.contextmanager
  def scope(self, node):
    """Context manager to handle a parenthesized scope."""
    self.open_scope(node)
    yield
    self.close_scope(node)

  def is_in_scope(self):
    """Return True iff there is a scope open."""
    return self._parens or self._hints

  def str(self):
    """Parse a full string literal from the input."""
    def predicate(token):
      return (token[0] in (TOKENS.STRING, TOKENS.COMMENT) or
              self.is_in_scope() and token[0] in (TOKENS.NL, TOKENS.NEWLINE))

    content = ''
    prev_loc = self._loc
    tok = None
    for tok in self.takewhile(predicate, advance=False):
      content += self._space_between(prev_loc, tok)
      content += tok[1]
      prev_loc = tok[3]

    if tok:
      self._loc = tok[3]
    return content

  def _space_between(self, prev_loc, tok):
    """Parse the space between a location and the next token"""
    if prev_loc > tok[2]:
      raise ValueError('prev_loc > token start', prev_loc, tok[2])
    if prev_loc[0] > len(self._lines):
      return ''
    return ast_utils.space_between(prev_loc, tok[2],
                                   self._lines[prev_loc[0] - 1], self._lines)

  def next_name(self):
    """Parse the next name token."""
    last_i = self._i
    def predicate(token):
      return token[0] != TOKENS.NAME

    unused_tokens = list(self.takewhile(predicate, advance=False))
    result = self.next(advance=False)
    self._i = last_i
    return result

  def next_of_type(self, token_type):
    """Parse a token of the given type and return it."""
    token = self.next()
    if token[0] != token_type:
      raise ValueError("Expected %r but found %r\nline %d: %s" % (
          tokenize.tok_name[token_type], token[1], token[2][0],
          self._lines[token[2][0] - 1]))
    return token

  def takewhile(self, condition, advance=True):
    """Parse tokens as long as a condition holds on the next token."""
    token = self.next(advance=advance)
    while token is not None and condition(token):
      yield token
      token = self.next(advance=advance)
    self.rewind()


def _scope_helper(node):
  """Get the closure of nodes that could begin a scope at this point.

  For instance, when encountering a `(` when parsing a BinOp node, this could
  indicate that the BinOp itself is parenthesized OR that the BinOp's left node
  could be parenthesized.

  E.g.: (a + b * c)   or   (a + b) * c   or   (a) + b * c
        ^                  ^                  ^

  Arguments:
    node: (ast.AST) Node encountered when opening a scope.

  Returns:
    A closure of nodes which that scope might apply to.
  """
  if isinstance(node, ast.Attribute):
    return (node,) + _scope_helper(node.value)
  if isinstance(node, ast.Assign):
    return (node,) + _scope_helper(node.targets[0])
  if isinstance(node, ast.AugAssign):
    return (node,) + _scope_helper(node.target)
  if isinstance(node, ast.Expr):
    return (node,) + _scope_helper(node.value)
  if isinstance(node, ast.Compare):
    return (node,) + _scope_helper(node.left)
  if isinstance(node, ast.BoolOp):
    return (node,) + _scope_helper(node.values[0])
  if isinstance(node, ast.BinOp):
    return (node,) + _scope_helper(node.left)
  return (node,)
