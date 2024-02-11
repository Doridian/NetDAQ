from dataclasses import dataclass, field
from enum import Enum

from .equation import DAQEquation
from .base import ConfigError

@dataclass(frozen=True, kw_only=True)
class DAQEquationTokenTypeDC:
    id: int
    prev: list[int]

class DAWEquationTokenType(Enum):
    UNKNOWN = DAQEquationTokenTypeDC(id=0, prev=[])
    CHANNEL = DAQEquationTokenTypeDC(id=1, prev=[0, 2, 5])
    OPERATOR = DAQEquationTokenTypeDC(id=2, prev=[1, 4, 6])
    FUNCTION = DAQEquationTokenTypeDC(id=3, prev=[0, 2, 5])
    FLOAT = DAQEquationTokenTypeDC(id=4, prev=[0, 2, 5])
    OPENING_BRACKET = DAQEquationTokenTypeDC(id=5, prev=[0, 2, 3, 5])
    CLOSING_BRACKET = DAQEquationTokenTypeDC(id=6, prev=[1, 4, 6])
    END = DAQEquationTokenTypeDC(id=7, prev=[1, 4, 6])

UNARY_OPERATORS = ["+", "-"]
OPERATORS = ["+", "-", "*", "^", "**", "/"]
FUNCTIONS = ["exp", "ln", "log", "abs", "int", "sqrt"]

OPTERATOR_PRECEDENCE = {
    "+": 1,
    "-": 1,
    "*": 2,
    "/": 2,
    "^": 3,
    "**": 3,
}

@dataclass(frozen=True, kw_only=True)
class DAQEquationToken:
    token: str
    token_type: DAWEquationTokenType
    begin: int
    end: int
    begins_with_whitespace: bool

    def validate(self) -> None:
        if self.token_type == DAWEquationTokenType.UNKNOWN:
            raise ConfigError(f"Unknown token type for token {self.token}")
        elif self.token_type == DAWEquationTokenType.CHANNEL:
            if self.token[0] != "c":
                raise ConfigError(f"Invalid channel token (does not begin with c) {self.token}")
            try:
                n = int(self.token[1:])
                if n <= 0:
                    raise ConfigError(f"Invalid channel token (channel number must be greater than 0) {self.token}")
            except ValueError:
                raise ConfigError(f"Invalid channel token {self.token}")
        elif self.token_type == DAWEquationTokenType.FLOAT:
            try:
                _ = float(self.token)
            except ValueError:
                raise ConfigError(f"Invalid float token {self.token}")
        elif self.token_type == DAWEquationTokenType.OPERATOR:    
            if self.token not in OPERATORS:
                raise ConfigError(f"Invalid operator token {self.token}")
        elif self.token_type == DAWEquationTokenType.FUNCTION:
            if self.token not in FUNCTIONS:
                raise ConfigError(f"Invalid function token {self.token}")

@dataclass
class DAQEquationTokenTreeNode:
    nodes: list["DAQEquationTokenTreeNode"] = field(default_factory=lambda: [])
    value: DAQEquationToken | None = None

    def print_tree(self, indent: str = '') -> None:
        if self.value:
            print(f"{indent}{self.value.token}")
        for node in self.nodes:
            node.print_tree(indent + '  ')

class DAQEQuationCompiler:
    def __init__(self) -> None:
        super().__init__()

    def compile(self, src: str) -> DAQEquation | None:
        tokens = self.tokenize(src)
        tokens = self.integrate_unary_minusplus(tokens)
        self.validate_token_order(tokens)
        token_tree = self.build_token_tree(tokens.copy())
        self.simplify_token_tree(token_tree)
        token_tree.print_tree()

    # Turn tree into only subtrees of the form "X" or "X", <OP>, "Y"
    def simplify_token_tree(self, token_tree: DAQEquationTokenTreeNode) -> None:
        for node in token_tree.nodes:
            self.simplify_token_tree(node)

        if len(token_tree.nodes) == 1 and not token_tree.value:
            token_tree.value = token_tree.nodes[0].value
            token_tree.nodes = token_tree.nodes[0].nodes
            return

        # 1-3 node subtrees cannot be simplified
        if len(token_tree.nodes) < 4:
            return

        # We must now be in a leaf node of the form "X", <OP>, "Y", <OP>, "Z", ...
        best_operator: int | None = None
        best_operator_precedence: int = 0
        for i, sub_node in enumerate(token_tree.nodes):
            if not sub_node.value or sub_node.value.token_type != DAWEquationTokenType.OPERATOR:
                continue
            this_operator_precedence = OPTERATOR_PRECEDENCE[sub_node.value.token]
            if this_operator_precedence <= best_operator_precedence:
                continue
            best_operator = i
            best_operator_precedence = this_operator_precedence

        assert best_operator is not None

        new_tree_left = DAQEquationTokenTreeNode(nodes=token_tree.nodes[:best_operator])
        new_tree_op = DAQEquationTokenTreeNode(value=token_tree.nodes[best_operator].value)
        new_tree_right = DAQEquationTokenTreeNode(nodes=token_tree.nodes[best_operator+1:])

        self.simplify_token_tree(new_tree_left)
        self.simplify_token_tree(new_tree_right)

        token_tree.nodes = [
            new_tree_left,
            new_tree_op,
            new_tree_right,
        ]

    def build_token_tree(self, tokens: list[DAQEquationToken], *, value: DAQEquationToken | None = None) -> DAQEquationTokenTreeNode:
        token_tree = DAQEquationTokenTreeNode(value=value)
    
        while tokens:
            token = tokens.pop(0)
            if token.token_type == DAWEquationTokenType.FUNCTION:
                token_must_be_bracket = tokens.pop(0)
                if (not token_must_be_bracket) or token_must_be_bracket.token_type != DAWEquationTokenType.OPENING_BRACKET:
                    raise ConfigError(f"Invalid expression (function {token.token} must be followed by an opening bracket)")
                token_tree.nodes.append(self.build_token_tree(tokens, value=token))
                continue
            if token.token_type == DAWEquationTokenType.OPENING_BRACKET:
                token_tree.nodes.append(self.build_token_tree(tokens))
                continue
            elif token.token_type == DAWEquationTokenType.CLOSING_BRACKET:
                break
            token_tree.nodes.append(DAQEquationTokenTreeNode(value=token))

        if len(token_tree.nodes) == 0:
            raise ConfigError(f"Invalid expression (empty bracket)")
        # Just return single child node if this is a bare bracket (no function)
        elif len(token_tree.nodes) == 1 and token_tree.value is None:
            return token_tree.nodes[0]

        return token_tree

    def validate_token_order(self, tokens: list[DAQEquationToken]) -> None:
        bracket_counter: int = 0

        for i, token in enumerate(tokens):
            if token.token_type == DAWEquationTokenType.OPENING_BRACKET:
                bracket_counter += 1
            elif token.token_type == DAWEquationTokenType.CLOSING_BRACKET:
                bracket_counter -= 1
                if bracket_counter < 0:
                    raise ConfigError(f"Invalid expression (closing bracket without opening bracket) {token.token}")

            prev_token = tokens[i-1] if i > 0 else None
            prev_token_id = prev_token.token_type.value.id if prev_token else 0
            if prev_token_id not in token.token_type.value.prev:
                raise ConfigError(f"Invalid token order (token {token.token} cannot follow token {prev_token.token if prev_token else "BEGIN"})")

        if len(tokens) > 0:
            last_token = tokens[-1]
            if last_token.token_type.value.id not in DAWEquationTokenType.END.value.prev:
                raise ConfigError(f"Invalid token order (token {last_token.token} cannot be the last token in the expression)")

        if bracket_counter != 0:
            raise ConfigError(f"Invalid expression (unclosed brackets)")

    def integrate_unary_minusplus(self, tokens: list[DAQEquationToken]) -> list[DAQEquationToken]:
        new_tokens: list[DAQEquationToken] = []
        for i, token in enumerate(tokens):
            new_tokens.append(token)
            if token.token_type != DAWEquationTokenType.FLOAT:
                continue
            # Unary operators cannot have spaces between the number and operator
            if token.begins_with_whitespace:
                continue

            # Unary operators can only happen at the start, after an operator or after "("
            prev_prev_token = tokens[i-2] if i > 1 else None
            if prev_prev_token and prev_prev_token.token_type != DAWEquationTokenType.OPERATOR and prev_prev_token.token_type != DAWEquationTokenType.OPENING_BRACKET:
                continue

            # Is there a possibly unary operatoe before the float?
            prev_token = tokens[i-1] if i > 0 else None
            if not prev_token or prev_token.token_type != DAWEquationTokenType.OPERATOR or prev_token.token not in UNARY_OPERATORS:
                continue

            # If the previous token is a unary operator, we need to merge it with the float
            _ = new_tokens.pop() # Remove the float now at the top of new_tokens
            # Replace the float token with one with the operator
            new_token = DAQEquationToken(token=prev_token.token + token.token, token_type=DAWEquationTokenType.FLOAT, begin=prev_token.begin, end=token.end, begins_with_whitespace=False)
            new_token.validate()
            new_tokens[-1] = new_token
        return new_tokens

    def tokenize(self, src: str) -> list[DAQEquationToken]:
        tokens: list[DAQEquationToken] = []

        current_token_begin: int = 0
        current_token_str: str = ""
        current_token_match_type: int = 0
        current_token_beings_with_whitespace: bool = False
        current_token_type: DAWEquationTokenType = DAWEquationTokenType.UNKNOWN

        def push_token_validate(token: DAQEquationToken) -> None:
            token.validate()
            tokens.append(token)

        def push_current_token(*, pos: int, push_also: str = "", token_type: DAWEquationTokenType = DAWEquationTokenType.UNKNOWN):
            nonlocal current_token_str
            nonlocal current_token_match_type
            nonlocal current_token_type
            nonlocal current_token_begin
            nonlocal current_token_beings_with_whitespace
            if current_token_str:
                push_token_validate(DAQEquationToken(token=current_token_str, token_type=current_token_type, begin=current_token_begin, end=pos-1, begins_with_whitespace=current_token_beings_with_whitespace))
                current_token_str = ""
                current_token_type = token_type
                current_token_match_type = 0
                current_token_beings_with_whitespace = False  
            current_token_begin = pos          
            if push_also:
                push_token_validate(DAQEquationToken(token=push_also, token_type=token_type, begin=pos, end=pos, begins_with_whitespace=current_token_beings_with_whitespace))
                current_token_beings_with_whitespace = False

        def push_if_not_type(token_match_type: int, pos: int, token_type: DAWEquationTokenType = DAWEquationTokenType.UNKNOWN) -> None:
            nonlocal current_token_match_type
            nonlocal current_token_type
            if current_token_match_type != token_match_type:
                push_current_token(pos=pos, token_type=token_type)
            current_token_type = token_type
            current_token_match_type = token_match_type

        for i, c in enumerate(src.lower()):
            if c == "*":
                if current_token_str != "*" and current_token_str:
                    push_current_token(token_type=DAWEquationTokenType.OPERATOR, pos=i)
                current_token_type = DAWEquationTokenType.OPERATOR
                current_token_str += c
                if current_token_str == "**":
                    current_token_str = "^" # Push ** as ^
                    push_current_token(pos=i)
            elif c in OPERATORS:
                push_current_token(push_also=c, token_type=DAWEquationTokenType.OPERATOR, pos=i)
            elif c == "(":
                push_current_token(push_also=c, token_type=DAWEquationTokenType.OPENING_BRACKET, pos=i)
            elif c == ")":
                push_current_token(push_also=c, token_type=DAWEquationTokenType.CLOSING_BRACKET, pos=i)
            elif c in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."):
                ttype = DAWEquationTokenType.FLOAT
                if current_token_str and current_token_str[0] == "c":
                    ttype = DAWEquationTokenType.CHANNEL
                    if len(current_token_str) == 1:
                        current_token_match_type = 1 # Channels start with C and are followed by a number
                push_if_not_type(1, token_type=ttype, pos=i)
                current_token_str += c
            elif c == " ":
                push_current_token(pos=i)
                current_token_beings_with_whitespace = True
            else:
                push_if_not_type(2, token_type=DAWEquationTokenType.FUNCTION, pos=i)
                current_token_str += c

        push_current_token(pos=len(src))

        return tokens
