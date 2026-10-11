"""Read-only, token-aware SDF structural audit with explicit EOF diagnostics.

Quoted strings, escaped characters in identifiers, and comments are recognized;
parenthesis character counts alone are not an acceptance condition. No vendor
job or source correction is performed by this module.
"""
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent


@dataclass
class Token:
    kind: str
    text: str
    start: int
    end: int


@dataclass
class Node:
    start: int
    children: list = field(default_factory=list)
    end: int | None = None

    @property
    def name(self):
        if self.children and isinstance(self.children[0], Token):
            return self.children[0].text
        return None

    def direct(self, name):
        return [child for child in self.children
                if isinstance(child, Node) and child.name == name]


def tokens(text):
    """Lex SDF without interpreting quoted/escaped parentheses as syntax."""
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace() or (index == 0 and char == '\ufeff'):
            index += 1
            continue
        if text.startswith('//', index):
            stop = text.find('\n', index + 2)
            index = len(text) if stop < 0 else stop + 1
            continue
        if text.startswith('/*', index):
            stop = text.find('*/', index + 2)
            if stop < 0:
                raise ValueError(f'Unterminated block comment at {index}')
            index = stop + 2
            continue
        start = index
        if char in '()':
            index += 1
            yield Token(char, char, start, index)
            continue
        if char == '"':
            index += 1
            while index < len(text):
                if text[index] == '\\':
                    if index + 1 >= len(text):
                        raise ValueError(f'Dangling quoted escape at {index}')
                    index += 2
                elif text[index] == '"':
                    index += 1
                    yield Token('string', text[start:index], start, index)
                    break
                else:
                    index += 1
            else:
                raise ValueError(f'Unterminated quoted string at {start}')
            continue
        while index < len(text):
            char = text[index]
            if char == '\\':
                if index + 1 >= len(text):
                    raise ValueError(f'Dangling identifier escape at {index}')
                index += 2
            elif char.isspace() or char in '()':
                break
            elif char == '"':
                raise ValueError(f'Quote embedded in unquoted atom at {index}')
            else:
                index += 1
        assert index > start
        yield Token('atom', text[start:index], start, index)


def parse(text, allow_eof=False):
    roots, stack, lexical = [], [], []
    for token in tokens(text):
        lexical.append(token)
        if token.kind == '(':
            node = Node(token.start)
            if stack:
                stack[-1].children.append(node)
            else:
                roots.append(node)
            stack.append(node)
        elif token.kind == ')':
            if not stack:
                raise ValueError(f'Unexpected closing parenthesis at {token.start}')
            stack.pop().end = token.end
        else:
            if not stack:
                raise ValueError(f'Atom outside an SDF expression at {token.start}')
            stack[-1].children.append(token)
    if stack and not allow_eof:
        raise ValueError('Unclosed expressions at EOF: ' + ', '.join(str(n.name) for n in stack))
    return roots, stack, lexical


def leaves(node):
    for child in node.children:
        if isinstance(child, Token):
            yield child
        else:
            yield from leaves(child)


def instance(cell, text):
    found = cell.direct('INSTANCE')
    assert len(found) == 1 and found[0].end is not None
    item = found[0]
    assert all(isinstance(c, Token) for c in item.children)
    return text[item.children[0].end:item.end - 1].strip(), item


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def describe(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    text = data.decode('utf-8')
    roots, open_nodes, lexical = parse(text, allow_eof=True)
    assert len(roots) == 1 and roots[0].name == 'DELAYFILE'
    top = roots[0]
    cells = top.direct('CELL')
    assert cells, 'No direct top-level CELLs'
    for cell in cells:
        assert len(cell.direct('CELLTYPE')) == 1
        instance(cell, text)
        assert len(cell.direct('DELAY')) == 1
    names = [instance(cell, text)[0] for cell in cells]
    assert len(set(names)) == len(names)
    repaired = text + ('\n' + ')' * len(open_nodes) + '\n' if open_nodes else '')
    repaired_roots, still_open, repaired_lexical = parse(repaired)
    assert not still_open
    assert [(t.kind, t.text) for t in repaired_lexical[:len(lexical)]] == [(t.kind, t.text) for t in lexical]
    assert all(t.kind == ')' for t in repaired_lexical[len(lexical):])
    repaired_cells = repaired_roots[0].direct('CELL')
    assert len(repaired_cells) == len(cells)
    for before, after in zip(cells, repaired_cells):
        # Every atom/string (including all endpoint and delay expressions) is
        # unchanged. Only already-open structural expressions are closed.
        assert [(t.kind, t.text) for t in leaves(before)] == [(t.kind, t.text) for t in leaves(after)]
        if before.end is not None:
            assert text[before.start:before.end] == repaired[after.start:after.end]
    positions = []
    for node in open_nodes:
        line = text.count('\n', 0, node.start) + 1
        col = node.start - text.rfind('\n', 0, node.start)
        positions.append(dict(expression=node.name, line=line, column=col,
                              character_offset=node.start,
                              opening_line=text.splitlines()[line - 1]))
    result = dict(path=str(path), source_sha256=sha_bytes(data), bytes=len(data),
                  lexical_tokens=len(lexical), strict_structurally_balanced=not open_nodes,
                  direct_root_cell_count=len(cells), complete_cell_count=sum(c.end is not None for c in cells),
                  incomplete_cell_instances=[instance(c, text)[0] for c in cells if c.end is None],
                  unclosed_expressions_at_EOF=positions,
                  EOF_only_added_closing_parentheses=len(open_nodes),
                  EOF_only_repair_preserves_every_original_token=True,
                  EOF_only_repair_preserves_all_original_cell_atoms_paths_delays_checks=True,
                  cell_instances_sha256=sha_bytes('\n'.join(names).encode()),
                  repair_is_not_original_SDF_acceptance=True)
    return result, text, repaired, repaired_roots[0]


def self_check():
    good = '(DELAYFILE (DESIGN "quoted ( and ) \\" inner") (CELL (CELLTYPE "x") (INSTANCE a\\(b\\)) (DELAY (ABSOLUTE (IOPATH A Z (1) (2))))) /* ignored () */ )'
    roots, opened, _ = parse(good)
    assert not opened and len(roots[0].direct('CELL')) == 1
    assert instance(roots[0].direct('CELL')[0], good)[0] == r'a\(b\)'
    try:
        parse(good[:-1])
    except ValueError as error:
        assert 'Unclosed expressions' in str(error)
    else:
        raise AssertionError('Truncation not detected')
    for bad in ['(DELAYFILE "unclosed)', '(DELAYFILE /* unclosed)', '(DELAYFILE) )']:
        try:
            parse(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid lexical/structural case accepted')


def main():
    self_check()
    target = P / 'sdf_structure_audit_v1.json'
    assert not target.exists(), 'Retain immutable audit snapshots'
    original = P.parent.parent / 'sequential_paper_trial/hardware/export12_e2_a0/routed.sdf'
    fixed16 = sorted((P.parent / 'width16').rglob('routed.sdf'))
    results = [describe(path)[0] for path in [original, *fixed16]]
    record = dict(status='completed_read_only_structural_audit',
                  parser='Token/quoted-string/escaped-identifier/comment-aware nested expression parser',
                  parser_self_checks_passed=True, source_files_modified=False,
                  vendor_tools_launched=False, width16_SDFs_present_at_snapshot=len(fixed16),
                  original_and_present_fixed16=results,
                  parser_sha256=sha_bytes(Path(__file__).read_bytes()),
                  limitation='A lexical/structural defect does not prove the cause of a simulator arithmetic discrepancy. Newly generated files require a new audit snapshot.')
    target.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
