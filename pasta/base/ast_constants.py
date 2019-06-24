"""Constants relevant to ast code."""

import ast

NODE_TYPE_TO_TOKENS = {
    ast.Add: ('+',),
    ast.Sub: ('-',),
    ast.Mult: ('*',),
    ast.Div: ('/',),
    ast.Mod: ('%',),
    ast.BitAnd: ('&',),
    ast.BitOr: ('|',),
    ast.BitXor: ('^',),
    ast.FloorDiv: ('//',),
    ast.Pow: ('**',),
    ast.LShift: ('<<',),
    ast.RShift: ('>>',),
    ast.BitAnd: ('&',),
    ast.BitOr: ('|',),
    ast.BitXor: ('^',),
    ast.FloorDiv: ('//',),
    ast.Invert: ('~',),
    ast.Not: ('not',),
    ast.UAdd: ('+',),
    ast.USub: ('-',),
    ast.And: ('and',),
    ast.Or: ('or',),
    ast.Eq: ('==',),
    ast.NotEq: ('!=',),
    ast.Lt: ('<',),
    ast.LtE: ('<=',),
    ast.Gt: ('>',),
    ast.GtE: ('>=',),
    ast.Is: ('is',),
    ast.IsNot: ('is', 'not',),
    ast.In: ('in',),
    ast.NotIn: ('not', 'in',),
}


if hasattr(ast, 'MatMult'):
  NODE_TYPE_TO_TOKENS[ast.MatMult] = ('@',)
