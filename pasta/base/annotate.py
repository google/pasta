# coding=utf-8
"""Annotate python syntax trees with formatting from the soruce file."""
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

import abc
import ast
import collections
import contextlib
import itertools
import six
from six.moves import zip
import tokenize

try:
  from StringIO import StringIO
except ImportError:  # py3k
  from io import StringIO

from pasta.base import ast_utils

# Alias for extracting token names
TOKENS = tokenize


def parenthesizable(f):
  """Decorates a function where the node visited can be wrapped in parens."""
  @contextlib.wraps(f)
  def wrapped(self, node, *args, **kwargs):
    with self.scope(node):
      self.prefix(node)
      f(self, node, *args, **kwargs)
      self.suffix(node, oneline=True)
  return wrapped


def spaced(f):
  """Decorates a function where the node visited can have space around it."""
  @contextlib.wraps(f)
  def wrapped(self, node, *args, **kwargs):
    self.prefix(node)
    f(self, node, *args, **kwargs)
    self.suffix(node, oneline=True)
  return wrapped


class BaseVisitor(ast.NodeVisitor):

  __metaclass__ = abc.ABCMeta

  def visit(self, node):
    ast_utils.setup_props(node)
    super(BaseVisitor, self).visit(node)

  def suffix(self, node, oneline=False):
    self.attr(node, 'suffix', [lambda: self.ws(oneline=oneline)])

  def prefix(self, node):
    self.attr(node, 'prefix', [self.ws])

  def ws(self, oneline=False):
    return ''

  @abc.abstractmethod
  def token():
    pass

  @abc.abstractmethod
  def optional_suffix():
    pass

  @spaced
  def visit_Module(self, node):
    self.generic_visit(node)
    self.attr(node, 'suffix', [self.ws])

  @parenthesizable
  def visit_Str(self, node):
    self.attr(node, 'content', [self.str])

  @abc.abstractmethod
  def visit_Num(self, node):
    pass

  @parenthesizable
  def visit_Expr(self, node):
    self.visit(node.value)

  @parenthesizable
  def visit_Tuple(self, node):
    for elt in node.elts:
      self.visit(elt)
      self.suffix(elt)
      if elt != node.elts[-1]:
        self.token(',')
    if node.elts:
      self.optional_suffix(node, 'extracomma', ',')

  @parenthesizable
  def visit_Assign(self, node):
    for target in node.targets:
      self.visit(target)
      self.suffix(target)
      self.token('=')
    self.visit(node.value)

  @parenthesizable
  def visit_AugAssign(self, node):
    self.visit(node.target)
    self.suffix(node.target)
    # TODO Better approach for this
    if isinstance(node.op, ast.Add):
      self.token('+=')
    elif isinstance(node.op, ast.Sub):
      self.token('-=')
    elif isinstance(node.op, ast.Mult):
      self.token('*=')
    elif isinstance(node.op, ast.Div):
      self.token('/=')
    elif isinstance(node.op, ast.Mod):
      self.token('%=')
    elif isinstance(node.op, ast.BitAnd):
      self.token('&=')
    elif isinstance(node.op, ast.BitOr):
      self.token('|=')
    elif isinstance(node.op, ast.BitXor):
      self.token('^=')
    elif isinstance(node.op, ast.FloorDiv):
      self.token('//=')
    elif isinstance(node.op, ast.Pow):
      self.token('**=')
    else:
      raise ValueError('Unable to parse AugAssign op: ' + node.op)
    self.visit(node.value)

  @parenthesizable
  def visit_BinOp(self, node):
    self.visit(node.left)
    self.suffix(node.left)
    self.visit(node.op)
    self.visit(node.right)
    self.suffix(node.right)

  @parenthesizable
  def visit_BoolOp(self, node):
    for value in node.values:
      self.visit(value)
      if value != node.values[-1]:
        self.suffix(value)
        self.visit(node.op)

  @parenthesizable
  def visit_UnaryOp(self, node):
    self.visit(node.op)
    self.visit(node.operand)

  @parenthesizable
  def visit_Lambda(self, node):
    self.token('lambda')
    self.visit(node.args)
    self.token(':')
    self.visit(node.body)

  @spaced
  def visit_Import(self, node):
    self.token('import')
    for alias in node.names:
      self.visit(alias)
      if alias != node.names[-1]:
        self.suffix(alias)
        self.token(',')

  @spaced
  def visit_ImportFrom(self, node):
    self.token('from')
    self.attr(node, 'module_prefix', [self.ws], default=' ')

    module_pattern = ['.', self.ws] * node.level
    if node.module:
      parts = node.module.split('.')
      for part in parts[:-1]:
        module_pattern += [self.ws, part, '.']
      module_pattern += [self.ws, parts[-1]]

    self.attr(node, 'module', module_pattern,
              deps=('level', 'module'),
              default='.' * node.level + (node.module or ''))
    self.attr(node, 'module_suffix', [self.ws], default=' ')

    self.token('import')
    for alias in node.names:
      self.visit(alias)
      if alias != node.names[-1]:
        self.token(',')

  @parenthesizable
  def visit_Compare(self, node):
    self.visit(node.left)
    for op, comparator in zip(node.ops, node.comparators):
      self.visit(op)
      self.visit(comparator)

  def visit_Add(self, node):
    self.token('+')

  def visit_Sub(self, node):
    self.token('-')

  def visit_Mult(self, node):
    self.token('*')

  def visit_Div(self, node):
    self.token('/')

  def visit_Mod(self, node):
    self.token('%')

  def visit_Pow(self, node):
    self.token('**')

  def visit_LShift(self, node):
    self.token('<<')

  def visit_RShift(self, node):
    self.token('>>')

  def visit_BitAnd(self, node):
    self.token('&')

  def visit_BitOr(self, node):
    self.token('|')

  def visit_BitXor(self, node):
    self.token('^')

  def visit_FloorDiv(self, node):
    self.token('//')

  def visit_Invert(self, node):
    self.token('~')

  def visit_Not(self, node):
    self.token('not')

  def visit_UAdd(self, node):
    self.token('+')

  def visit_USub(self, node):
    self.token('-')

  def visit_And(self, node):
    self.token('and')

  def visit_Or(self, node):
    self.token('or')

  @spaced
  def visit_Eq(self, node):
    self.token('==')

  @spaced
  def visit_NotEq(self, node):
    self.token('!=')

  @spaced
  def visit_Lt(self, node):
    self.token('<')

  @spaced
  def visit_LtE(self, node):
    self.token('<=')

  @spaced
  def visit_Gt(self, node):
    self.token('>')

  @spaced
  def visit_GtE(self, node):
    self.token('>=')

  @spaced
  def visit_Is(self, node):
    self.token('is')

  @spaced
  def visit_IsNot(self, node):
    self.attr(node, 'content', ['is', self.ws, 'not'], default='is not')

  @spaced
  def visit_In(self, node):
    self.token('in')

  @spaced
  def visit_NotIn(self, node):
    self.attr(node, 'content', ['not', self.ws, 'in'], default='not in')

  @spaced
  def visit_alias(self, node):
    self.token(node.name)
    if node.asname is not None:
      self.attr(node, 'asname', [self.ws, 'as', self.ws], default=' as ')
      self.token(node.asname)

  @spaced
  def visit_If(self, node):
    self.token('elif' if ast_utils.prop(node, 'is_elif') else 'if')
    self.visit(node.test)
    self.attr(node, 'testsuffix', [self.ws, ':', self.ws], default=':')
    for stmt in node.body:
      self.visit(stmt)

    if node.orelse:
      if (len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If) and
          self.check_is_elif(node.orelse[0])):
        ast_utils.setprop(node.orelse[0], 'is_elif', True)
        self.visit(node.orelse[0])
      else:
        self.attr(node, 'elseprefix', [self.ws])
        self.token('else')
        self.attr(node, 'elsesuffix', [self.ws, ':', self.ws], default=':')
        for stmt in node.orelse:
          self.visit(stmt)

  @abc.abstractmethod
  def check_is_elif(self):
    pass

  @parenthesizable
  def visit_IfExp(self, node):
    self.visit(node.body)
    self.suffix(node.body)
    self.token('if')
    self.visit(node.test)
    self.suffix(node.test)
    self.token('else')
    self.visit(node.orelse)

  @spaced
  def visit_While(self, node):
    self.token('while')
    self.visit(node.test)
    self.attr(node, 'testsuffix', [self.ws, ':', self.ws], default=':')
    for stmt in node.body:
      self.visit(stmt)

    if node.orelse:
      self.attr(node, 'elseprefix', [self.ws])
      self.token('else')
      self.attr(node, 'elsesuffix', [self.ws, ':', self.ws], default=':')
      for stmt in node.orelse:
        self.visit(stmt)

  @spaced
  def visit_For(self, node):
    self.token('for')
    self.visit(node.target)
    self.suffix(node.target)
    self.token('in')
    self.visit(node.iter)
    self.suffix(node.iter)
    self.token(':')
    for stmt in node.body:
      self.visit(stmt)

    if node.orelse:
      self.attr(node, 'orelseprefix', [self.ws])
      self.token('else')
      self.token(':')

      for stmt in node.orelse:
        self.visit(stmt)

  @spaced
  def visit_Repr(self, node):
    raise NotImplementedError()

  @spaced
  def visit_With(self, node):
    if hasattr(node, 'items'):
      return self.visit_With_3(node)
    if not getattr(node, 'is_continued', False):
      self.token('with')
    self.visit(node.context_expr)
    self.suffix(node.context_expr)
    if node.optional_vars:
      self.token('as')
      self.visit(node.optional_vars)
      self.suffix(node.optional_vars)

    if self.check_is_continued_with(node.body[0]):
      node.body[0].is_continued = True
      self.token(',')
    else:
      self.token(':')

    for stmt in node.body:
      self.visit(stmt)

  @abc.abstractmethod
  def check_is_continued_with(self, unused_node):
    pass

  @spaced
  def visit_With_3(self, node):
    self.token('with')

    for i, withitem in enumerate(node.items):
      self.visit(withitem)
      if i != len(node.items) - 1:
        self.token(',')

    self.token(':')
    for stmt in node.body:
      self.visit(stmt)

  @spaced
  def visit_withitem(self, node):
    self.visit(node.context_expr)
    self.suffix(node.context_expr)
    if node.optional_vars:
      self.token('as')
      self.visit(node.optional_vars)
      self.suffix(node.optional_vars)

  @spaced
  def visit_Assert(self, node):
    self.token('assert')
    self.visit(node.test)
    if node.msg:
      self.token(',')
      self.visit(node.msg)

  @spaced
  def visit_Exec(self, node):
    raise NotImplementedError()

  @spaced
  def visit_Global(self, node):
    self.token('global')

  @parenthesizable
  def visit_Name(self, node):
    self.token(node.id)

  @parenthesizable
  def visit_NameConstant(self, node):
    self.token(str(node.value))

  @parenthesizable
  def visit_Attribute(self, node):
    self.visit(node.value)
    self.attr(node, 'dot', [self.ws, '.', self.ws], default='.')
    self.token(node.attr)

  @parenthesizable
  def visit_Subscript(self, node):
    self.visit(node.value)
    self.visit(node.slice)

  @spaced
  def visit_Index(self, node):
    self.token('[')
    self.visit(node.value)
    self.suffix(node.value)
    self.token(']')

  @spaced
  def visit_Slice(self, node):
    self.token('[')

    if node.lower:
      self.visit(node.lower)
      self.suffix(node.lower)
    else:
      self.attr(node, 'lowerspace', [self.ws])

    if node.lower or node.upper:
      self.token(':')

    if node.upper:
      self.visit(node.upper)
      self.suffix(node.upper)
    else:
      self.attr(node, 'upperspace', [self.ws])

    if node.step:
      self.token(':')
      self.visit(node.step)
      self.suffix(node.step)
    else:
      self.attr(node, 'stepspace', [self.ws])

    self.token(']')

  @parenthesizable
  def visit_List(self, node):
    self.token('[')

    for elt in node.elts:
      self.visit(elt)
      self.suffix(elt)
      if elt != node.elts[-1]:
        self.token(',')
    if node.elts:
      self.optional_suffix(node, 'extracomma', ',')

    self.attr(node, 'close_prefix', [self.ws])
    self.token(']')

  @parenthesizable
  def visit_Set(self, node):
    self.token('{')

    for elt in node.elts:
      self.visit(elt)
      self.suffix(elt)
      if elt != node.elts[-1]:
        self.token(',')
    if node.elts:
      self.optional_suffix(node, 'extracomma', ',')

    self.token('}')

  @parenthesizable
  def visit_Dict(self, node):
    self.token('{')

    for key, value in zip(node.keys, node.values):
      self.visit(key)
      self.suffix(key)
      self.token(':')
      self.visit(value)
      if value != node.values[-1]:
        self.suffix(value)
        self.token(',')
    self.optional_suffix(node, 'extracomma', ',')
    self.attr(node, 'close_prefix', [self.ws])
    self.token('}')

  @parenthesizable
  def visit_GeneratorExp(self, node):
    self.visit(node.elt)
    self.suffix(node.elt)
    for comp in node.generators:
      self.token('for')
      self.visit(comp)

  @parenthesizable
  def visit_ListComp(self, node):
    self._comp_exp(node, open_brace='[', close_brace=']')

  @parenthesizable
  def visit_SetComp(self, node):
    self._comp_exp(node, open_brace='{', close_brace='}')

  def _comp_exp(self, node, open_brace=None, close_brace=None):
    if open_brace:
      self.token(open_brace)
    self.visit(node.elt)
    self.suffix(node.elt)
    for comp in node.generators:
      self.token('for')
      self.visit(comp)
    if close_brace:
      self.token(close_brace)

  @parenthesizable
  def visit_DictComp(self, node):
    self.token('{')
    self.visit(node.key)
    self.suffix(node.key)
    self.token(':')
    self.visit(node.value)
    self.suffix(node.value)
    for comp in node.generators:
      self.token('for')
      self.visit(comp)
    self.token('}')

  @spaced
  def visit_comprehension(self, node):
    self.visit(node.target)
    self.suffix(node.target)
    self.token('in')
    self.visit(node.iter)
    self.suffix(node.iter)
    for if_expr in node.ifs:
      self.token('if')
      self.visit(if_expr)
      if if_expr != node.ifs[-1]:
        self.suffix(if_expr)

  @parenthesizable
  def visit_Call(self, node):
    self.visit(node.func)
    self.suffix(node.func)
    self.token('(')
    num_items = (len(node.args) + len(node.keywords) +
                 (1 if node.starargs else 0) + (1 if node.kwargs else 0))
    i = 0

    for arg in node.args:
      self.visit(arg)
      self.suffix(arg)
      if i < num_items - 1:
        self.token(',')
      i += 1

    starargs_idx = ast_utils.find_starargs(node)
    kw_end = len(node.args) + len(node.keywords) + (1 if node.starargs else 0)
    kw_idx = 0
    while i < kw_end:
      if i == starargs_idx:
        self.attr(node, 'starargs_prefix', [self.ws, '*'], default='*')
        self.visit(node.starargs)
        self.suffix(node.starargs)
      else:
        self.visit(node.keywords[kw_idx])
        self.suffix(node.keywords[kw_idx])
        kw_idx += 1
      if i < num_items - 1:
        self.token(',')
      i += 1

    if node.kwargs:
      self.attr(node, 'kwargs_prefix', [self.ws, '**'], default='**')
      self.visit(node.kwargs)
      self.suffix(node.kwargs)

    if num_items > 0:
      self.optional_suffix(node, 'extracomma', ',')

    self.token(')')

  @spaced
  def visit_arguments(self, node):
    total_args = (len(node.args) +
                  (1 if node.vararg else 0) + 
                  (1 if node.kwarg else 0))
    arg_i = 0
    
    positional = node.args[:-len(node.defaults)] if node.defaults else node.args
    keyword = node.args[-len(node.defaults):] if node.defaults else node.args

    for arg in positional:
      self.visit(arg)
      self.suffix(arg)
      arg_i += 1
      if arg_i < total_args:
        self.token(',')

    for arg, default in zip(keyword, node.defaults):
      self.visit(arg)
      self.suffix(arg)
      self.token('=')
      self.visit(default)
      self.suffix(default)
      arg_i += 1
      if arg_i < total_args:
        self.token(',')

    if node.vararg:
      self.attr(node, 'vararg_prefix', [self.ws, '*', self.ws], default='*')
      if isinstance(node.vararg, ast.AST):
        self.visit(node.vararg)
      else:
        self.token(node.vararg)
        self.attr(node, 'vararg_suffix', [self.ws])
      arg_i += 1
      if arg_i < total_args:
        self.token(',')

    if node.kwarg:
      self.attr(node, 'kwarg_prefix', [self.ws, '**', self.ws], default='**')
      if isinstance(node.kwarg, ast.AST):
        self.visit(node.kwarg)
      else:
        self.token(node.kwarg)
        self.attr(node, 'kwarg_suffix', [self.ws])

  @spaced
  def visit_arg(self, node):
    self.token(node.arg)
    self.suffix(node)
    if node.annotation is not None:
      self.token(':')
      self.visit(node.annotation)

  @spaced
  def visit_FunctionDef(self, node):
    for decorator in node.decorator_list:
      self.token('@')
      self.visit(decorator)
      self.suffix(decorator)
    self.token('def')
    self.attr(node, 'name_prefix', [self.ws])
    self.token(node.name)
    self.attr(node, 'name_suffix', [self.ws])
    self.token('(')
    self.visit(node.args)
    self.token(')')

    if getattr(node, 'returns', None):
      self.attr(node, 'returns_prefix', [self.ws, '->', self.ws],
                deps=('returns',), default=' -> ')
      self.visit(node.returns)

    self.token(':')

    for expr in node.body:
      self.visit(expr)

  @spaced
  def visit_keyword(self, node):
    self.token(node.arg)
    self.attr(node, 'eq', [self.ws, '='], default='=')
    self.visit(node.value)

  @spaced
  def visit_Return(self, node):
    self.token('return')
    if node.value:
      self.visit(node.value)

  @spaced
  def visit_Yield(self, node):
    self.token('yield')
    if node.value:
      self.visit(node.value)

  @spaced
  def visit_Delete(self, node):
    self.token('del')
    for target in node.targets:
      self.visit(target)
      self.suffix(target)
      if target != node.targets[-1]:
        self.token(',')

  @spaced
  def visit_Print(self, node):
    self.token('print')
    self.attr(node, 'print_suffix', [self.ws], default=' ')
    if node.dest:
      self.token('>>')
      self.visit(node.dest)
      if node.values or not node.nl:
        self.suffix(node.dest)
        self.token(',')

    for value in node.values:
      self.visit(value)
      if value != node.values[-1] or not node.nl:
        self.suffix(value)
        self.token(',')

  @spaced
  def visit_ClassDef(self, node):
    for decorator in node.decorator_list:
      self.token('@')
      self.visit(decorator)
      self.suffix(decorator)
    self.token('class')
    self.attr(node, 'name_prefix', [self.ws], default=' ')
    self.token(node.name)
    self.attr(node, 'name_suffix', [self.ws])
    self.token('(')
    for base in node.bases:
      self.visit(base)
      self.suffix(base)
      if base != node.bases[-1]:
        self.token(',')
    self.token(')')
    self.token(':')

    for expr in node.body:
      self.visit(expr)

  @spaced
  def visit_Pass(self, node):
    self.token('pass')

  @spaced
  def visit_Break(self, node):
    self.token('break')

  @spaced
  def visit_Continue(self, node):
    self.token('continue')

  @spaced
  def visit_TryFinally(self, node):
    # Try with except and finally is a TryFinally with the first statement as a
    # TryExcept in Python2
    if not isinstance(node.body[0], ast.TryExcept):
      self.attr(node, 'open_try', ['try', self.ws, ':'], default='try:')
    for stmt in node.body:
      self.visit(stmt)
    self.attr(node, 'open_finally', ['finally', self.ws, ':'],
              default='finally:')
    for stmt in node.finalbody:
      self.visit(stmt)

  @spaced
  def visit_TryExcept(self, node):
    self.attr(node, 'open_try', ['try', self.ws, ':'], default='try:')
    for stmt in node.body:
      self.visit(stmt)
    for handler in node.handlers:
      self.visit(handler)
    if node.orelse:
      self.attr(node, 'open_else', ['else', self.ws, ':'], default='else:')
      for stmt in node.orelse:
        self.visit(stmt)

  @spaced
  def visit_Try(self, node):
    # Python 3
    self.attr(node, 'open_try', ['try', self.ws, ':'], default='try:')
    for stmt in node.body:
      self.visit(stmt)
    for handler in node.handlers:
      self.visit(handler)
    if node.orelse:
      self.attr(node, 'open_else', ['else', self.ws, ':'], default='else:')
      for stmt in node.orelse:
        self.visit(stmt)
    if node.finalbody:
      self.attr(node, 'open_finally', ['finally', self.ws, ':'],
                default='finally:')
      for stmt in node.finalbody:
        self.visit(stmt)

  @spaced
  def visit_ExceptHandler(self, node):
    self.token('except')
    if node.type:
      self.visit(node.type)
      self.suffix(node.type)
    if node.type and node.name:
      self.attr(node, 'as', [self.ws, 'as', self.ws], default=' as ')
    if node.name:
      if isinstance(node.name, ast.AST):
        self.visit(node.name)
      else:
        self.token(node.name)
        self.attr(node, 'name_suffix', [self.ws])
    self.token(':')
    for stmt in node.body:
      self.visit(stmt)

  @spaced
  def visit_Raise(self, node):
    self.token('raise')
    if node.type:
      self.visit(node.type)
    if node.inst:
      self.suffix(node.type)
      self.token(',')
      self.visit(node.inst)
    if node.tback:
      self.suffix(node.inst)
      self.token(',')
      self.visit(node.tback)

  def check_is_continued_with(self, node):
    return isinstance(node, ast.With) and self.tokens.peek()[1] == ','

  def _ws(self):
    return self.tokens.whitespace()

  @contextlib.contextmanager
  def scope(self, node):
    yield

  def str(self):
    pass


class AstAnnotator(BaseVisitor):

  def __init__(self, source):
    self.tokens = TokenGenerator(source)

  @parenthesizable
  def visit_Num(self, node):
    contentargs = [lambda: self._skip(TOKENS.NUMBER)]
    if node.n < 0:
      contentargs.insert(0, '-')
    self.attr(node, 'content', contentargs, deps=('n',), default=str(node.n))

  def check_is_elif(self, node):
    next_tok = self.tokens.next_name()
    return isinstance(node, ast.If) and next_tok[1] == 'elif'

  def ws(self, oneline=False):
    return self.tokens.whitespace(oneline=oneline)

  def token(self, token_val):
    token = self.tokens.next()
    if token[1] != token_val:
      raise ValueError("Expected %r but found %r\nline %d: %s" % (
          token_val, token[1], token[2][0], self.tokens._lines[token[2][0] - 1]))

    if token[1] in '({[':
      self.tokens.hint_open()
    elif token[1] in ')}]':
      self.tokens.hint_closed()

    return token[1]

  def optional_suffix(self, node, attr_name, token_val):
    token = self.tokens.peek()
    if token[1] == token_val:
      self.tokens.next()
      ast_utils.appendprop(node, attr_name, token[1] + self.ws())

  def attr(self, node, attr_name, attr_vals, deps=None, default=None):
    if deps:
      for dep in deps:
        ast_utils.setprop(node, dep + '__src', getattr(node, dep, None))
    for attr_val in attr_vals:
      if attr_val == ' ':
        attr_val = self.ws
      if isinstance(attr_val, six.string_types):
        ast_utils.appendprop(node, attr_name, self.token(attr_val))
      else:
        ast_utils.appendprop(node, attr_name, attr_val())

  def _skip(self, token_type):
    token = self.tokens.next()
    if not token[0] == token_type:
      raise ValueError("Expected %r but found %r\nline %d: %s" % (
          tokenize.tok_name[token_type], token[1], token[2][0],
          self.tokens._lines[token[2][0] - 1]))
    return token[1]

  def _optional_suffix(self, token_type, token_val):
    token = self.tokens.peek()
    if token[0] != token_type or token[1] != token_val:
      return ''
    else:
      self.tokens.next()
      return token[1] + self.ws()
  
  def scope(self, node):
    return self.tokens.scope(node)

  def str(self):
    return self.tokens.str()

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
    if self._i < 0:
      return (1, 0)
    return self._tokens[self._i][2]

  def loc_end(self):
    if self._i < 0:
      return (1, 0)
    return self._tokens[self._i][3]

  def peek(self):
    if self._i >= self._len:
      return None
    return self._tokens[self._i + 1]
  
  def next(self, advance=True):
    self._i += 1
    if self._i >= self._len:
      return None
    if advance:
      self._loc = self._tokens[self._i][3]
    return self._tokens[self._i]

  def rewind(self, amount=1):
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
      return token[0] in (TOKENS.NL, TOKENS.NEWLINE, TOKENS.COMMENT, TOKENS.INDENT) or token[1] in '('
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
      return (token[0] in (TOKENS.NL, TOKENS.NEWLINE, TOKENS.COMMENT,\
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
    self.open_scope(node)
    yield
    self.close_scope(node)

  def is_in_scope(self):
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

    tokens = list(self.takewhile(predicate, advance=False))
    result = self.next(advance=False)
    self._i = last_i
    return result
  
  def takewhile(self, condition, advance=True):
    """Parse tokens as long as a condition holds on the next token."""
    token = self.next(advance=advance)
    while token is not None and condition(token):
      yield token
      token = self.next(advance=advance)
    self.rewind()


def _scope_helper(node):
  """Get the closure of nodes that could begin a scope at this point."""
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
