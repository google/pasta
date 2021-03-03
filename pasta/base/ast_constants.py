"""Constants relevant to ast code."""

def get_node_type_to_tokens(astlib):
  result = {
      astlib.Add: ('+',),
      astlib.And: ('and',),
      astlib.BitAnd: ('&',),
      astlib.BitOr: ('|',),
      astlib.BitXor: ('^',),
      astlib.Div: ('/',),
      astlib.Eq: ('==',),
      astlib.FloorDiv: ('//',),
      astlib.Gt: ('>',),
      astlib.GtE: ('>=',),
      astlib.In: ('in',),
      astlib.Invert: ('~',),
      astlib.Is: ('is',),
      astlib.IsNot: (
          'is',
          'not',
      ),
      astlib.LShift: ('<<',),
      astlib.Lt: ('<',),
      astlib.LtE: ('<=',),
      astlib.Mod: ('%',),
      astlib.Mult: ('*',),
      astlib.Not: ('not',),
      astlib.NotEq: ('!=',),
      astlib.NotIn: (
          'not',
          'in',
      ),
      astlib.Or: ('or',),
      astlib.Pow: ('**',),
      astlib.RShift: ('>>',),
      astlib.Sub: ('-',),
      astlib.UAdd: ('+',),
      astlib.USub: ('-',),
  }
  if hasattr(astlib, 'MatMult'):
    result[astlib.MatMult] = ('@',)
  return result
