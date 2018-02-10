import sys, math

from fractions import *
from modgrammar import *

sympy = "--sympy" in sys.argv

if sympy: import sympy
else: import mpmath

if sympy:
	to_float = sympy.Rational
	to_complex = lambda a, b: sympy.Rational(a) + sympy.Rational(b) * sympy.I
else:
	to_float = mpmath.mpf
	to_complex = mpmath.mpc

class NZD(Grammar):
	grammar = L("1") | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"

class HexDigit(Grammar):
	grammar = L("0") | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "a" | "A" | "b" | "B" | "c" | "C" | "d" | "D" | "e" | "E" | "f" | "F"

def number_format(digits):
	g = L(digits[0])
	for i in digits[1:]:
		g |= i
	g = REPEAT(g)
	return OR((g, ".", g), (OPTIONAL("."), g))

class DecimalNumber(Grammar):
	grammar = OR(("0", ".", WORD("0-9")), (NZD, OPTIONAL(number_format("0123456789"))))

class OctalNumber(Grammar):
	grammar = ("0", number_format("01234567"))

class BinaryNumber(Grammar):
	grammar = (L("0") | (NZD, OPTIONAL(WORD("0-9"))), "b", number_format("01"))

class ExtOctalNumber(Grammar):
	grammar = (L("0") | (NZD, OPTIONAL(WORD("0-9"))), "o", number_format("01234567"))

class HexNumber(Grammar):
	grammar = (L("0") | (NZD, OPTIONAL(WORD("0-9"))), "x", number_format("0123456789abcdefABCDEF"))

class String(Grammar):
	grammar = OR(("\"", REPEAT(OR(ANY_EXCEPT("\""), ("\\", ANY))), "\""), ("'", REPEAT(OR(ANY_EXCEPT("'"), ("\\", ANY), "'"))))

class Number(Grammar):
	grammar = (DecimalNumber | BinaryNumber | HexNumber | ExtOctalNumber | OctalNumber, OPTIONAL("j"))

class Literal(Grammar):
	grammar = String | Number

class Keyword(Grammar):
	grammar = OR("if", "else", "for", "while", "unless", "until", "class")

class Identifier(Grammar):
	grammar = WORD("A-Za-z_", "A-Za-z_0-9")

class Value(Grammar):
	grammar = Identifier | Literal

class Exponent(Grammar):
	grammar = LIST_OF(REF("Expr") | Value, sep = "**", grammar_whitespace_mode = "optional")

class Product(Grammar):
	grammar = LIST_OF(REF("Expr") | Exponent, sep = OR("*", "/", "/_", "%"), grammar_whitespace_mode = "optional")

class Sum(Grammar):
	grammar = LIST_OF(REF("Expr") | Product, sep = OR("+", "-"), grammar_whitespace_mode = "optional")

class Expr(Grammar):
	grammar = ("(", Sum | Product | Value, ")")

class Expression(Grammar):
	grammar = Expr | Sum | Product | Value

class GetterWrapper:
	def __init__(self, object = None):
		self.object = object
	def __call__(self, index):
		if self.object is None:
			raise AttributeError("NoneType object has no _real_ attributes")
		else:
			return getattr(self.object, index)
	def __str__(self):
		return str(self.object)

class ProtonObject:
	def __init__(self, parent = None, attrs = None):
		self.parent = GetterWrapper(parent)
		self.attrs = attrs or {}
	def __call__(self, index):
		if index in self.attrs:
			return self.attrs[index]
		else:
			return self.parent(index)
	def __str__(self):
		return str(self.parent)

def base_convert(string, base, indexstr = None):
	if "." in string or indexstr:
		indexstr = indexstr or "0123456789abcdefghijklmnopqrstuvwxyz"
		val = to_float(0)
		mul = 1
		for c in string[:string.find(".")][::-1]:
			val += mul * indexstr.find(c)
			mul *= base
		mul = to_float("1/%d" % base)
		for c in string[string.find(".") + 1:]:
			val += mul * indexstr.find(c)
			mul /= base
		return val
	else:
		return int(string, base)

def get_reducers(d):
	return {e: reducer(d[e]) for e in d}

def reducer(name):
	return (lambda val: val(name)) if isinstance(name, str) else name

def chain_attempts(*getters):
	for g in getters:
		try:
			return g()
		except:
			pass
	return None

def floor(val):
	try:
		return val.__floor__()
	except:
		return val - val % 1

def global_eval(node, nest_level = 0, global_values = {}, scope = {}):
	evaluate = lambda node: global_eval(node, nest_level + 1, global_values, scope)
	def fold(node, reducers, reverse = False):
		values = list(map(evaluate, list(node[0])[::2]))
		operators = list(map(str, list(node[0])[1::2]))[::-1 if reverse else 1]
		if reverse:
			for i in range(len(values) - 2, -1, -1):
				values[i] = ProtonObject(reducers[operators.pop(0)](values[i])(values[i + 1].parent.object))
			return values[0]
		else:
			for i in range(1, len(values)):
				values[0] = ProtonObject(reducers[operators.pop(0)](values[0])(values[i].parent.object))
			return values[0]
	if node.grammar_name == "Expression":
		return evaluate(node[0])
	elif node.grammar_name == "Expr":
		return evaluate(node[1])
	elif node.grammar_name == "Exponent":
		return fold(node, get_reducers({"**": "__pow__"}), True)
	elif node.grammar_name == "Product":
		return fold(node, get_reducers({"*": "__mul__", "/": "__div__", "/_": lambda val: chain_attempts(lambda: val("__floordiv__"), lambda: lambda a: floor(val("__div__")(a))), "%": "__mod__"}))
	elif node.grammar_name == "Sum":
		return fold(node, get_reducers({"+": "__add__", "-": "__sub__"}))
	elif node.grammar_name == "Value":
		return evaluate(node[0])
	elif node.grammar_name == "Literal":
		return evaluate(node[0])
	elif node.grammar_name == "Number":
		return ProtonObject(evaluate(node[0]) * (1j if node[1] else 1))
	elif node.grammar_name == "HexNumber":
		s = str(node).split("x")
		return base_convert(s[1].lower(), 16) * 16 ** int(s[0])
	elif node.grammar_name == "BinaryNumber":
		s = str(node).split("b")
		return base_convert(s[1].lower(), 2) * 2 ** int(s[0])
	elif node.grammar_name == "ExtOctalNumber":
		s = str(node).split("o")
		return base_convert(s[1].lower(), 8) * 8 ** int(s[0])
	elif node.grammar_name == "OctalNumber":
		return base_convert(str(node)[1:].lower(), 8)
	elif node.grammar_name == "DecimalNumber":
		return to_float(str(node))
	elif node.grammar_name == "String":
		return ProtonObject(eval(str(node)))

def remove_comments(string):
	return string # TODO make this actually work

Expression.grammar_resolve_refs()

grammar_whitespace_mode = "optional"

print(global_eval(Expression.parser().parse_string(remove_comments(sys.stdin.read().strip()))))