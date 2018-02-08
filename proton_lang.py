import sys

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
	return Grammar(g, ".", g) | (OPTIONAL("."), g)

class DecimalNumber(Grammar):
	grammar = (NZD, number_format("0123456789"))

class OctalNumber(Grammar):
	grammar = ("0", number_format("01234567"))

class BinaryNumber(Grammar):
	grammar = (L("0") | (NZD, WORD("0-9")), "b", number_format("01"))

class HexNumber(Grammar):
	grammar = (L("0") | (NZD, WORD("0-9")), "x", number_format("0123456789abcdefABCDEF"))

class Number(Grammar):
	grammar = DecimalNumber | BinaryNumber | HexNumber | OctalNumber

print(repr(Number.parser().parse_string("0x1f")))
