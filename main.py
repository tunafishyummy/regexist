r"""
Regexist - a minimal regular expression engine (console demo).

Group 7 - Nullscapes (Julongbayan, Lamio, Rojo, Suyo, Timmalog)
CS 200 - Principles of Programming Languages

Run:  python main.py

What it does:
  1. reads a pattern and a sample text from the user
  2. scanner  -> turns the pattern into tokens
  3. parser   -> builds a parse tree (and checks for errors)
  4. automaton-> builds an NFA using Thompson's construction
  5. matcher  -> runs the text through the NFA (no backtracking)

Supported: literals, concatenation, alternation |, repetition * + ?,
character sets and ranges [aeiou] [a-z], anchors ^ $, class escapes
\d \w \s, escaped literals, and capturing groups ( ). Every match in
the text is listed, not only the first one.
"""

DIGITS = frozenset("0123456789")
WORD = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
SPACE = frozenset(" \t\n\r\f\v")
ESCAPE_SETS = {"d": DIGITS, "w": WORD, "s": SPACE}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class LexicalError(Exception):
    pass


class RegexSyntaxError(Exception):
    pass


class SemanticError(Exception):
    pass


# ---------------------------------------------------------------------------
# Scanner (lexer) - Section 4.3
# ---------------------------------------------------------------------------
class Token:
    def __init__(self, kind, value, position):
        self.kind = kind
        self.value = value
        self.position = position


class Scanner:
    def __init__(self, pattern):
        self.pattern = pattern

    def tokenize(self):
        tokens = []
        i = 0
        n = len(self.pattern)
        while i < n:
            ch = self.pattern[i]
            if ch == "\\":
                if i + 1 >= n:
                    raise LexicalError("incomplete escape sequence", i)
                nxt = self.pattern[i + 1]
                if nxt in "dws":
                    tokens.append(Token("CLASS_ESCAPE", nxt, i))
                else:
                    tokens.append(Token("ESCAPED_LITERAL", nxt, i))
                i += 2
            elif ch == "[":
                j = i + 1
                items = []
                while j < n and self.pattern[j] != "]":
                    items.append(self.pattern[j])
                    j += 1
                if j >= n:
                    raise LexicalError("unterminated character set", i)
                charset = self._build_set(items, i)
                tokens.append(Token("CHARCLASS", charset, i))
                i = j + 1
            elif ch == "(":
                tokens.append(Token("GROUP_START", "(", i)); i += 1
            elif ch == ")":
                tokens.append(Token("GROUP_END", ")", i)); i += 1
            elif ch == "|":
                tokens.append(Token("ALT", "|", i)); i += 1
            elif ch == "*":
                tokens.append(Token("STAR", "*", i)); i += 1
            elif ch == "+":
                tokens.append(Token("PLUS", "+", i)); i += 1
            elif ch == "?":
                tokens.append(Token("QUESTION", "?", i)); i += 1
            elif ch == "^":
                tokens.append(Token("ANCHOR_START", "^", i)); i += 1
            elif ch == "$":
                tokens.append(Token("ANCHOR_END", "$", i)); i += 1
            else:
                tokens.append(Token("LITERAL", ch, i)); i += 1
        return tokens

    def _build_set(self, items, pos):
        if len(items) == 0:
            raise SemanticError("empty character set", pos)
        chars = set()
        k = 0
        while k < len(items):
            if k + 2 < len(items) and items[k + 1] == "-":
                lo, hi = items[k], items[k + 2]
                if ord(lo) > ord(hi):
                    raise SemanticError('range "%s-%s" is out of order' % (lo, hi), pos)
                for code in range(ord(lo), ord(hi) + 1):
                    chars.add(chr(code))
                k += 3
            else:
                chars.add(items[k])
                k += 1
        return frozenset(chars)


# ---------------------------------------------------------------------------
# Parser - Section 4.4
# ---------------------------------------------------------------------------
class Node:
    def __init__(self, kind, value=None, children=None):
        self.kind = kind
        self.value = value
        self.children = children or []


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.group_count = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self):
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def parse(self):
        node = self.parse_alternation()
        if self.pos != len(self.tokens):
            token = self.tokens[self.pos]
            if token.kind == "GROUP_END":
                raise RegexSyntaxError("unmatched ')'", token.position)
            raise RegexSyntaxError("unexpected token '%s'" % token.value, token.position)
        return node

    def parse_alternation(self):
        branches = [self.parse_concatenation()]
        while self.peek() is not None and self.peek().kind == "ALT":
            alt = self.advance()
            nxt = self.peek()
            if nxt is None or nxt.kind in ("ALT", "GROUP_END"):
                raise RegexSyntaxError("empty branch in alternation", alt.position)
            branches.append(self.parse_concatenation())
        if len(branches) == 1:
            return branches[0]
        return Node("alt", children=branches)

    def parse_concatenation(self):
        items = []
        while True:
            token = self.peek()
            if token is None or token.kind in ("ALT", "GROUP_END"):
                break
            items.append(self.parse_repetition())
        if len(items) == 0:
            token = self.peek()
            if token is not None and token.kind == "GROUP_END":
                raise RegexSyntaxError("unmatched ')'", token.position)
            raise RegexSyntaxError("empty pattern", 0)
        if len(items) == 1:
            return items[0]
        return Node("concat", children=items)

    def parse_repetition(self):
        node = self.parse_atom()
        while True:
            token = self.peek()
            if token is not None and token.kind in ("STAR", "PLUS", "QUESTION"):
                self.advance()
                op = {"STAR": "star", "PLUS": "plus", "QUESTION": "opt"}[token.kind]
                node = Node(op, children=[node])
            else:
                break
        return node

    def parse_atom(self):
        token = self.peek()
        if token is None:
            raise RegexSyntaxError("unexpected end of pattern", 0)
        if token.kind in ("STAR", "PLUS", "QUESTION"):
            raise RegexSyntaxError("nothing to repeat before '%s'" % token.value, token.position)
        if token.kind == "GROUP_START":
            self.advance()
            self.group_count += 1
            index = self.group_count
            inner = self.parse_alternation()
            end = self.peek()
            if end is None or end.kind != "GROUP_END":
                raise RegexSyntaxError("unmatched '('", token.position)
            self.advance()
            return Node("group", value=index, children=[inner])
        if token.kind == "GROUP_END":
            raise RegexSyntaxError("unmatched ')'", token.position)
        self.advance()
        if token.kind in ("LITERAL", "ESCAPED_LITERAL"):
            return Node("literal", value=token.value)
        if token.kind == "CHARCLASS":
            return Node("class", value=token.value)
        if token.kind == "CLASS_ESCAPE":
            return Node("class", value=ESCAPE_SETS[token.value])
        if token.kind == "ANCHOR_START":
            return Node("anchor_start")
        if token.kind == "ANCHOR_END":
            return Node("anchor_end")
        raise RegexSyntaxError("unexpected token '%s'" % token.value, token.position)


def print_tree(node, indent):
    if node.kind == "literal":
        print(indent + "literal '%s'" % node.value)
    elif node.kind == "class":
        print(indent + "class [%s]" % "".join(sorted(node.value)))
    elif node.kind in ("star", "plus", "opt"):
        label = {"star": "star (*)", "plus": "plus (+)", "opt": "optional (?)"}[node.kind]
        print(indent + label)
        print_tree(node.children[0], indent + "  ")
    elif node.kind == "concat":
        print(indent + "concat")
        for child in node.children:
            print_tree(child, indent + "  ")
    elif node.kind == "alt":
        print(indent + "alternation")
        for child in node.children:
            print_tree(child, indent + "  ")
    elif node.kind == "group":
        print(indent + "group %d" % node.value)
        print_tree(node.children[0], indent + "  ")
    elif node.kind == "anchor_start":
        print(indent + "anchor ^")
    elif node.kind == "anchor_end":
        print(indent + "anchor $")


# ---------------------------------------------------------------------------
# NFA - Thompson's construction - Section 4.5
# ---------------------------------------------------------------------------
class State:
    def __init__(self, sid):
        self.id = sid
        self.eps = []      # list of (target_id, action)
        self.trans = []    # list of (matcher, target_id)


class NFA:
    def __init__(self):
        self.states = []

    def new_state(self):
        state = State(len(self.states))
        self.states.append(state)
        return state


def build_nfa(node, nfa):
    kind = node.kind
    if kind == "literal" or kind == "class":
        start = nfa.new_state()
        end = nfa.new_state()
        start.trans.append((node.value, end.id))
        return start.id, end.id
    if kind == "anchor_start" or kind == "anchor_end":
        start = nfa.new_state()
        end = nfa.new_state()
        action = ("assert_start",) if kind == "anchor_start" else ("assert_end",)
        start.eps.append((end.id, action))
        return start.id, end.id
    if kind == "concat":
        first = None
        prev_end = None
        for child in node.children:
            child_start, child_end = build_nfa(child, nfa)
            if first is None:
                first = child_start
            else:
                nfa.states[prev_end].eps.append((child_start, None))
            prev_end = child_end
        return first, prev_end
    if kind == "alt":
        start = nfa.new_state()
        end = nfa.new_state()
        for child in node.children:
            child_start, child_end = build_nfa(child, nfa)
            start.eps.append((child_start, None))
            nfa.states[child_end].eps.append((end.id, None))
        return start.id, end.id
    if kind == "star":
        start = nfa.new_state()
        end = nfa.new_state()
        child_start, child_end = build_nfa(node.children[0], nfa)
        start.eps.append((child_start, None))
        start.eps.append((end.id, None))
        nfa.states[child_end].eps.append((child_start, None))
        nfa.states[child_end].eps.append((end.id, None))
        return start.id, end.id
    if kind == "plus":
        start = nfa.new_state()
        end = nfa.new_state()
        child_start, child_end = build_nfa(node.children[0], nfa)
        start.eps.append((child_start, None))
        nfa.states[child_end].eps.append((child_start, None))
        nfa.states[child_end].eps.append((end.id, None))
        return start.id, end.id
    if kind == "opt":
        start = nfa.new_state()
        end = nfa.new_state()
        child_start, child_end = build_nfa(node.children[0], nfa)
        start.eps.append((child_start, None))
        start.eps.append((end.id, None))
        nfa.states[child_end].eps.append((end.id, None))
        return start.id, end.id
    if kind == "group":
        start = nfa.new_state()
        end = nfa.new_state()
        child_start, child_end = build_nfa(node.children[0], nfa)
        start.eps.append((child_start, ("save", 2 * node.value)))
        nfa.states[child_end].eps.append((end.id, ("save", 2 * node.value + 1)))
        return start.id, end.id
    raise ValueError("unknown node type: %s" % kind)


# ---------------------------------------------------------------------------
# Matcher - run the text through the NFA - Section 4.5
# ---------------------------------------------------------------------------
def char_matches(matcher, ch):
    if isinstance(matcher, frozenset):
        return ch in matcher
    return matcher == ch


class Matcher:
    def __init__(self, nfa, start, accept, group_count):
        self.nfa = nfa
        self.start = start
        self.accept = accept
        self.group_count = group_count

    def closure(self, threads, pos, text_len):
        result = dict(threads)
        stack = list(threads.items())
        while stack:
            sid, caps = stack.pop()
            for target, action in self.nfa.states[sid].eps:
                if action is not None:
                    if action[0] == "assert_start" and pos != 0:
                        continue
                    if action[0] == "assert_end" and pos != text_len:
                        continue
                new_caps = caps
                if action is not None and action[0] == "save":
                    slot = action[1]
                    values = list(caps)
                    values[slot] = pos
                    new_caps = tuple(values)
                if target not in result:
                    result[target] = new_caps
                    stack.append((target, new_caps))
        return result

    def match_at(self, text, start_pos):
        caps = tuple([None] * (2 * (self.group_count + 1)))
        active = self.closure({self.start: caps}, start_pos, len(text))
        best = None
        if self.accept in active:
            best = (start_pos, start_pos, active[self.accept])
        pos = start_pos
        while pos < len(text) and active:
            ch = text[pos]
            nxt = {}
            for sid, caps in active.items():
                for matcher, target in self.nfa.states[sid].trans:
                    if char_matches(matcher, ch) and target not in nxt:
                        nxt[target] = caps
            active = self.closure(nxt, pos + 1, len(text))
            pos += 1
            if self.accept in active:
                best = (start_pos, pos, active[self.accept])
        return best

    def search(self, text, from_pos=0):
        for start_pos in range(from_pos, len(text) + 1):
            result = self.match_at(text, start_pos)
            if result is not None:
                return result
        return None

    def find_all(self, text):
        matches = []
        from_pos = 0
        while from_pos <= len(text):
            result = self.search(text, from_pos)
            if result is None:
                break
            if result[0] == result[1] and matches and result[0] == matches[-1][1]:
                from_pos = result[0] + 1
                continue
            matches.append(result)
            from_pos = result[1] if result[1] > result[0] else result[0] + 1
        return matches


# ---------------------------------------------------------------------------
# Console UI
# ---------------------------------------------------------------------------
def format_token(token):
    if token.kind == "CHARCLASS":
        return "CHARCLASS[%s]" % "".join(sorted(token.value))
    if token.kind in ("LITERAL", "ESCAPED_LITERAL"):
        return "LITERAL(%s)" % token.value
    if token.kind == "CLASS_ESCAPE":
        return "CLASS_ESCAPE(\\%s)" % token.value
    return token.kind


def main():
    print("=" * 46)
    print("      Regexist - Regular Expression Engine")
    print("=" * 46)
    pattern = input("Enter a regular expression: ")
    if pattern == "":
        print("Runtime error: no pattern was entered")
        return
    text = input("Enter a sample text       : ")

    try:
        tokens = Scanner(pattern).tokenize()
    except LexicalError as error:
        print("Lexical error at position %d: %s" % (error.args[1], error.args[0]))
        return
    except SemanticError as error:
        print("Semantic error: %s" % error.args[0])
        return

    print("-" * 46)
    print("Tokens    : " + "  ".join(format_token(t) for t in tokens))

    try:
        parser = Parser(tokens)
        tree = parser.parse()
    except RegexSyntaxError as error:
        print("Syntax error at position %d: %s" % (error.args[1], error.args[0]))
        return
    except SemanticError as error:
        print("Semantic error: %s" % error.args[0])
        return

    print("Parse tree:")
    print_tree(tree, "  ")

    nfa = NFA()
    start, accept = build_nfa(tree, nfa)
    print("Build NFA : OK (%d states)" % len(nfa.states))

    matcher = Matcher(nfa, start, accept, parser.group_count)
    matches = matcher.find_all(text)
    if not matches:
        print("Result    : NO MATCH")
        return

    match_start, match_end, caps = matches[0]
    last = match_end - 1 if match_end > match_start else match_start
    print("Result    : MATCH")
    print('Matched   : "%s" at position %d-%d' % (text[match_start:match_end], match_start, last))
    for group in range(1, parser.group_count + 1):
        group_start = caps[2 * group]
        group_end = caps[2 * group + 1]
        if group_start is not None and group_end is not None:
            print('Group %d   : "%s"' % (group, text[group_start:group_end]))
    if len(matches) > 1:
        print("Other matches:")
        for other_start, other_end, _ in matches[1:]:
            other_last = other_end - 1 if other_end > other_start else other_start
            print('  "%s" at position %d-%d' % (text[other_start:other_end], other_start, other_last))


if __name__ == "__main__":
    main()
