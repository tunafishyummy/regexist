# Regexist

A regular expression engine built from scratch in Python. Regexist converts a
regular expression into a finite automaton and uses that machine to match a
sample text, so every stage of the process can be seen.

**Course:** CS 200 - Principles of Programming Languages
**Group:** 7 - Nullscapes
**Instructor:** Ms. Elsa V. Isip - Barcelos

## Overview

Most regular expression libraries hide how a pattern is processed. Regexist
shows the whole pipeline. The pattern is scanned into tokens, parsed into a
tree, converted into a nondeterministic finite automaton with Thompson's
construction, and then simulated over the text.

The engine uses only the Python standard library and runs as a single local
program.

## Features

- Literals and concatenation
- Alternation with `|`
- Repetition with `*`, `+` and `?`
- Character sets and ranges, such as `[aeiou]` and `[a-z]`
- Anchors `^` and `$`
- Class escapes `\d`, `\w` and `\s`
- Escaped literals, such as `\*`
- Capturing groups with `( )`
- Multiple matches reported from left to right
- Lexical, syntax, semantic and runtime errors with clear messages

## How it works

```
pattern and text
      |
      v
  Scanner      turns the pattern into tokens
      |
      v
  Parser       builds the parse tree and checks the semantic rules
      |
      v
  Automaton    builds an NFA with Thompson's construction
      |
      v
  Matcher      runs the text through the NFA without backtracking
      |
      v
  Result       MATCH or NO MATCH, positions and captured groups
```

## Supported syntax

| Element | Written as | Example |
|---|---|---|
| Literal | any non-special character | `abc` |
| Concatenation | elements in order | `cat` |
| Alternation | `\|` | `cat\|dog` |
| Zero or more | `*` | `ab*` |
| One or more | `+` | `ab+` |
| Optional | `?` | `colou?r` |
| Capturing group | `( )` | `(ab)+` |
| Character set | `[ ]` | `[aeiou]` |
| Range | `-` inside a set | `[a-z]` |
| Start anchor | `^` | `^ab` |
| End anchor | `$` | `ab$` |
| Class escape | `\d`, `\w`, `\s` | `\d+` |
| Escaped literal | `\` | `\*` |

Precedence runs from repetition, then concatenation, then alternation.
Parentheses can change the order.

## Requirements

Python 3. No external libraries and no internet connection are needed.

## Run

```bash
python main.py
```

On Linux or macOS, use:

```bash
python3 main.py
```

## Example

```
Enter a regular expression: (ab)+
Enter a sample text       : abab
```

The program prints the tokens, the parse tree, the NFA size and the result:

```
Result    : MATCH
Matched   : "abab" at position 0-3
Group 1   : "ab"
```

## Error handling

An invalid pattern is rejected before an automaton is built. Lexical, syntax,
semantic and runtime errors are reported with a message and, where possible,
the position of the problem.

| Error type | Example message |
|---|---|
| Lexical | `Lexical error at position 2: incomplete escape sequence` |
| Syntax | `Syntax error at position 0: nothing to repeat before '*'` |
| Semantic | `Semantic error: range "z-a" is out of order` |
| Runtime | `Runtime error: no pattern was entered` |

## Testing

The submitted version passed 19 test cases covering the core operators,
repetition, character sets and ranges, anchors, escapes, groups, multiple
matches and the three error categories.

## Limitations

- No backreferences or lookaround assertions
- No bounded repetition such as `{2,4}`
- No negated sets and no case-insensitive matching
- Matching only, without search and replace
- Leftmost, non-overlapping matches only
- Console interface

## Group 7 - Nullscapes

- Julongbayan, Dale Andre A.
- Lamio, Adinoel Rodge N.
- Rojo, Enzo Luis S.
- Suyo, Hadrian Kendrick S.
- Timmalog, John Joshua L.

The full project documentation, system design and test results are submitted
separately for CS 200.
