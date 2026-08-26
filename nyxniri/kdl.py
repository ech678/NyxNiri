import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class KdlValue:
    raw: str
    typ: str = "string"

    @property
    def value(self) -> Any:
        if self.typ == "int":
            return int(self.raw)
        if self.typ == "float":
            return float(self.raw)
        if self.typ == "bool":
            return self.raw.lower() in ("true", "yes", "on")
        if self.typ == "null":
            return None
        if self.typ == "color":
            return self.raw
        return self.raw.strip('"').strip("'")


@dataclass
class KdlNode:
    name: str = ""
    values: List[KdlValue] = field(default_factory=list)
    props: Dict[str, KdlValue] = field(default_factory=dict)
    children: List["KdlNode"] = field(default_factory=list)

    def child(self, name: str) -> Optional["KdlNode"]:
        for c in self.children:
            if c.name == name:
                return c
        return None

    def children_by_name(self, name: str) -> List["KdlNode"]:
        return [c for c in self.children if c.name == name]

    def get(self, key: str, default: Any = None) -> Any:
        if key in self.props:
            return self.props[key].value
        if self.values:
            return self.values[0].value
        return default


_TOKEN_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')
_TOKEN_SSTRING = re.compile(r"'((?:[^'\\]|\\.)*)'")
_TOKEN_COLOR = re.compile(r'#([0-9a-fA-F]{3,8})\b')
_TOKEN_NUMBER = re.compile(r'(-?(?:0x[0-9a-fA-F]+|0o[0-7]+|0b[01]+|\d+\.?\d*(?:[eE][+-]?\d+)?))')
_TOKEN_BOOL = re.compile(r'\b(true|false|yes|no|on|off)\b', re.IGNORECASE)
_TOKEN_NULL = re.compile(r'\b(null)\b', re.IGNORECASE)
_TOKEN_IDENT = re.compile(r'([a-zA-Z_][\w\-\.]*)')
_TOKEN_KEY = re.compile(r'([a-zA-Z_][\w\-\.]*)\s*=')

_NODE_END_CHARS = frozenset('{}()[];')
_QUOTE_CHARS = frozenset('"\'')
_ESCAPE_MAP = {
    'n': '\n',
    't': '\t',
    'r': '\r',
    '\\': '\\',
    '"': '"',
    "'": "'",
    's': ' ',
    '/': '/',
}


def _unescape(s: str) -> str:
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            nxt = s[i + 1]
            result.append(_ESCAPE_MAP.get(nxt, nxt))
            i += 2
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


def _classify_value(raw: str) -> KdlValue:
    raw = raw.strip()
    if not raw:
        return KdlValue(raw="", typ="null")
    if _TOKEN_BOOL.match(raw):
        return KdlValue(raw=raw, typ="bool")
    if _TOKEN_NULL.match(raw):
        return KdlValue(raw=raw, typ="null")
    if raw.startswith('#') and _TOKEN_COLOR.match(raw):
        return KdlValue(raw=raw, typ="color")
    if raw.startswith('"') or raw.startswith("'"):
        return KdlValue(raw=raw, typ="string")
    if _TOKEN_NUMBER.match(raw):
        if '.' in raw or 'e' in raw or 'E' in raw:
            return KdlValue(raw=raw, typ="float")
        return KdlValue(raw=raw, typ="int")
    return KdlValue(raw=raw, typ="string")


class _Tokenizer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def _skip_ws_and_comments(self, stop_at_newline: bool = False) -> None:
        while self.pos < self.length:
            ch = self.text[self.pos]
            if ch == '\n' and stop_at_newline:
                return
            if ch in ' \t\r\n':
                self.pos += 1
            elif ch == '/' and self.pos + 1 < self.length:
                nxt = self.text[self.pos + 1]
                if nxt == '/':
                    end = self.text.find('\n', self.pos)
                    self.pos = self.length if end == -1 else end + 1
                elif nxt == '*':
                    end = self.text.find('*/', self.pos + 2)
                    self.pos = self.length if end == -1 else end + 2
                else:
                    break
            else:
                break

    def _read_string(self, quote: str) -> str:
        self.pos += 1
        start = self.pos
        while self.pos < self.length:
            ch = self.text[self.pos]
            if ch == '\\' and self.pos + 1 < self.length:
                self.pos += 2
            elif ch == quote:
                raw = self.text[start:self.pos]
                self.pos += 1
                return _unescape(raw)
            else:
                self.pos += 1
        return _unescape(self.text[start:self.pos])

    def _read_bareword(self) -> str:
        start = self.pos
        while self.pos < self.length:
            ch = self.text[self.pos]
            if ch in ' \t\r\n{}();=\'"':
                break
            self.pos += 1
        return self.text[start:self.pos]

    def parse_node(self, top_level: bool = False) -> Optional[KdlNode]:
        while True:
            self._skip_ws_and_comments()
            if self.pos >= self.length:
                return None

            ch = self.text[self.pos]
            if ch == ';':
                self.pos += 1
                continue
            if ch == '}':
                return None
            if ch == '\n':
                self.pos += 1
                continue

            if ch == '"' or ch == "'":
                node = KdlNode(name=self._read_string(ch))
            else:
                bare = self._read_bareword()
                if not bare:
                    self.pos += 1
                    continue
                if bare.startswith('#') and len(bare) > 1:
                    node = KdlNode(name=bare)
                else:
                    node = KdlNode(name=bare)

            self._parse_node_body(node)
            if top_level:
                pass
            return node

    def _parse_node_body(self, node: KdlNode) -> None:
        while True:
            self._skip_ws_and_comments(stop_at_newline=True)
            if self.pos >= self.length:
                break
            ch = self.text[self.pos]
            if ch == ';':
                self.pos += 1
                break
            if ch == '{':
                self.pos += 1
                while True:
                    child = self.parse_node()
                    if child is None:
                        break
                    node.children.append(child)
                if self.pos < self.length and self.text[self.pos] == '}':
                    self.pos += 1
                break
            if ch == '}':
                break
            if ch == '\n':
                self.pos += 1
                break

            if ch == '"' or ch == "'":
                val = self._read_string(ch)
                node.values.append(KdlValue(raw=f'"{val}"', typ="string"))
                continue

            bare = self._read_bareword()
            if not bare:
                self.pos += 1
                continue

            saved = self.pos
            self._skip_ws_and_comments()
            if self.pos < self.length and self.text[self.pos] == '=':
                self.pos += 1
                self._skip_ws_and_comments()
                if self.pos < self.length:
                    vch = self.text[self.pos]
                    if vch == '"' or vch == "'":
                        vraw = f'"{self._read_string(vch)}"'
                        node.props[bare] = KdlValue(raw=vraw, typ="string")
                    else:
                        vbare = self._read_bareword()
                        node.props[bare] = _classify_value(vbare)
                continue
            else:
                self.pos = saved

            if bare.startswith('#') and len(bare) > 1:
                node.values.append(KdlValue(raw=bare, typ="color"))
            else:
                node.values.append(_classify_value(bare))


def parse(text: str) -> KdlNode:
    root = KdlNode(name="__root__")
    tok = _Tokenizer(text)
    while True:
        node = tok.parse_node(top_level=True)
        if node is None:
            break
        root.children.append(node)
    return root


def parse_file(path: str) -> KdlNode:
    with open(path, 'r', encoding='utf-8') as f:
        return parse(f.read())


def find_nodes(root: KdlNode, name: str, recursive: bool = False) -> List[KdlNode]:
    result = []
    for child in root.children:
        if child.name == name:
            result.append(child)
        if recursive:
            result.extend(find_nodes(child, name, recursive=True))
    return result


def to_dict(node: KdlNode) -> dict:
    d: Dict[str, Any] = {}
    for v in node.values:
        d.setdefault("_values", []).append(v.value)
    for k, v in node.props.items():
        d[k] = v.value
    for child in node.children:
        if child.name in d:
            if not isinstance(d[child.name], list):
                d[child.name] = [d[child.name]]
            d[child.name].append(to_dict(child))
        else:
            d[child.name] = to_dict(child)
    return d


def get_bind_info(node: KdlNode) -> dict:
    info = {"name": node.name}
    for k, v in node.props.items():
        info[k] = v.value
    info["args"] = [v.value for v in node.values]
    info["children"] = [c.name for c in node.children]
    return info


def extract_binds(root: KdlNode) -> List[dict]:
    binds_block = None
    for child in root.children:
        if child.name == "binds":
            binds_block = child
            break
    if binds_block is None:
        return []
    result = []
    for bind in binds_block.children:
        info = get_bind_info(bind)
        result.append(info)
    return result


def extract_environment(root: KdlNode) -> Dict[str, str]:
    env_block = None
    for child in root.children:
        if child.name == "environment":
            env_block = child
            break
    if env_block is None:
        return {}
    result = {}
    for child in env_block.children:
        if child.values:
            result[child.name] = child.values[0].value
    return result


def extract_spawn_startup(root: KdlNode) -> List[List[str]]:
    result = []
    for child in root.children:
        if child.name == "spawn-at-startup":
            result.append([v.value for v in child.values])
    return result


def extract_includes(root: KdlNode) -> List[dict]:
    result = []
    for child in root.children:
        if child.name == "include":
            entry = {"path": "", "optional": False}
            if child.values:
                entry["path"] = child.values[0].value
            if "optional" in child.props:
                entry["optional"] = child.props["optional"].value
            result.append(entry)
    return result