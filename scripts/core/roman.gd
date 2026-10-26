class_name Roman
extends RefCounted
## Roman numeral formatting for round counters.

const VALUES := [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
const SYMBOLS := ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]


static func to_roman(n: int) -> String:
	if n <= 0:
		return "0"
	var out := ""
	var rem := n
	for i in VALUES.size():
		while rem >= VALUES[i]:
			out += SYMBOLS[i]
			rem -= VALUES[i]
	return out
