from dataclasses import dataclass, field
from enum import Enum
from math import exp, log, log10, sqrt

from .equation import DAQEquation
from .base import ConfigError

@dataclass(frozen=True, kw_only=True)
class DAQEquationTokenTypeDC:
    id: int
    prev: list[int]

class DAQEquationTokenType(Enum):
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
    token_type: DAQEquationTokenType
    begin: int
    end: int
    begins_with_whitespace: bool

    def validate(self) -> None:
        if self.token_type == DAQEquationTokenType.UNKNOWN:
            raise ConfigError(f"Unknown token type for token {self.token}")
        elif self.token_type == DAQEquationTokenType.CHANNEL:
            if self.token[0] != "c":
                raise ConfigError(f"Invalid channel token (does not begin with c) {self.token}")
            try:
                n = int(self.token[1:])
                if n <= 0:
                    raise ConfigError(f"Invalid channel token (channel number must be greater than 0) {self.token}")
            except ValueError:
                raise ConfigError(f"Invalid channel token {self.token}")
        elif self.token_type == DAQEquationTokenType.FLOAT:
            try:
                _ = float(self.token)
            except ValueError:
                raise ConfigError(f"Invalid float token {self.token}")
        elif self.token_type == DAQEquationTokenType.OPERATOR:    
            if self.token not in OPERATORS:
                raise ConfigError(f"Invalid operator token {self.token}")
        elif self.token_type == DAQEquationTokenType.FUNCTION:
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
        self.resolve_constant_expression(token_tree)

        token_tree.print_tree()

        eq = DAQEquation()
        self._emit_tree(token_tree, eq)
        _ = eq.end()
        eq.validate()

        print(eq.encode())

    def _emit_token(self, token: DAQEquationToken, eq: DAQEquation) -> None:
        if token.token_type == DAQEquationTokenType.CHANNEL:
            _ = eq.push_channel(int(token.token[1:]))
        elif token.token_type == DAQEquationTokenType.FLOAT:
            _ = eq.push_float(float(token.token))
        elif token.token_type == DAQEquationTokenType.OPERATOR:
            if token.token == "+":
                _ = eq.add()
            elif token.token == "-":
                _ = eq.subtract()
            elif token.token == "*":
                _ = eq.multiply()
            elif token.token == "/":
                _ = eq.divide()
            elif token.token == "^" or token.token == "**":
                _ = eq.power()
        elif token.token_type == DAQEquationTokenType.FUNCTION:
            if token.token == "exp":
                _ = eq.exp()
            elif token.token == "ln":
                _ = eq.ln()
            elif token.token == "log":
                _ = eq.log()
            elif token.token == "abs":
                _ = eq.abs()
            elif token.token == "int":
                _ = eq.int()
            elif token.token == "sqrt":
                _ = eq.sqrt()

    def _emit_tree(self, token_tree: DAQEquationTokenTreeNode, eq: DAQEquation) -> None:
        if len(token_tree.nodes) == 1:
            self._emit_tree(token_tree.nodes[0], eq)
        elif len(token_tree.nodes) == 3:
            assert token_tree.nodes[1].value is not None
            self._emit_tree(token_tree.nodes[0], eq)
            self._emit_tree(token_tree.nodes[2], eq)
            self._emit_token(token_tree.nodes[1].value, eq)

        if token_tree.value:
            self._emit_token(token_tree.value, eq)

    # Turn tree into only subtrees of the form "X" or "X", <OP>, "Y"
    def simplify_token_tree(self, token_tree: DAQEquationTokenTreeNode) -> None:
        for node in token_tree.nodes:
            self.simplify_token_tree(node)

        self._simplify_token_tree_shallow(token_tree)

    def resolve_constant_expression(self, token_tree: DAQEquationTokenTreeNode) -> None:
        for node in token_tree.nodes:
            self.resolve_constant_expression(node)

        if len(token_tree.nodes) == 1:
            sub_node = token_tree.nodes[0]
            if not token_tree.value:
                token_tree.value = sub_node.value
                token_tree.nodes = sub_node.nodes
                return
            
            if (not sub_node.value) or sub_node.value.token_type != DAQEquationTokenType.FLOAT:
                return

            assert token_tree.value and token_tree.value.token_type == DAQEquationTokenType.FUNCTION

            token = sub_node.value
            token_value = float(token.token)
            if token.token == "exp":
                token_value = exp(token_value)
            elif token.token == "ln":
                token_value = log(token_value)
            elif token.token == "log":
                token_value = log10(token_value)
            elif token.token == "abs":
                token_value = abs(token_value)
            elif token.token == "int":
                token_value = float(int(token_value))
            elif token.token == "sqrt":
                token_value = sqrt(token_value)
            token_tree.value = token_tree.nodes[0].value
            token_tree.nodes = []

        if len(token_tree.nodes) != 3:
            return
        
        node_left = token_tree.nodes[0]
        node_right = token_tree.nodes[2]
        if node_left.value and node_left.value.token_type == DAQEquationTokenType.FLOAT and node_right.value and node_right.value.token_type == DAQEquationTokenType.FLOAT:
            value_left = float(node_left.value.token)
            value_right = float(node_right.value.token)
            new_float_value = 0.0
            op = token_tree.nodes[1].value
            assert op and op.token_type == DAQEquationTokenType.OPERATOR
            if op.token == "+":
                new_float_value = value_left + value_right
            elif op.token == "-":
                new_float_value = value_left - value_right
            elif op.token == "*":
                new_float_value = value_left * value_right
            elif op.token == "/":
                new_float_value = value_left / value_right
            elif op.token == "^" or op.token == "**":
                new_float_value = value_left ** value_right

            if token_tree.value:
                raise ValueError("Function calls on constants not supported, yet")
            
            token_tree.value = DAQEquationToken(token=str(new_float_value), token_type=DAQEquationTokenType.FLOAT, begin=node_left.value.begin, end=node_right.value.end, begins_with_whitespace=False)
            token_tree.nodes = []  

    def _simplify_token_tree_shallow(self, token_tree: DAQEquationTokenTreeNode) -> None:
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
            if not sub_node.value or sub_node.value.token_type != DAQEquationTokenType.OPERATOR:
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

        self._simplify_token_tree_shallow(new_tree_left)
        self._simplify_token_tree_shallow(new_tree_right)

        token_tree.nodes = [
            new_tree_left,
            new_tree_op,
            new_tree_right,
        ]

    def build_token_tree(self, tokens: list[DAQEquationToken], *, value: DAQEquationToken | None = None) -> DAQEquationTokenTreeNode:
        token_tree = DAQEquationTokenTreeNode(value=value)
    
        while tokens:
            token = tokens.pop(0)
            if token.token_type == DAQEquationTokenType.FUNCTION:
                token_must_be_bracket = tokens.pop(0)
                if (not token_must_be_bracket) or token_must_be_bracket.token_type != DAQEquationTokenType.OPENING_BRACKET:
                    raise ConfigError(f"Invalid expression (function {token.token} must be followed by an opening bracket)")
                token_tree.nodes.append(self.build_token_tree(tokens, value=token))
                continue
            if token.token_type == DAQEquationTokenType.OPENING_BRACKET:
                token_tree.nodes.append(self.build_token_tree(tokens))
                continue
            elif token.token_type == DAQEquationTokenType.CLOSING_BRACKET:
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
            if token.token_type == DAQEquationTokenType.OPENING_BRACKET:
                bracket_counter += 1
            elif token.token_type == DAQEquationTokenType.CLOSING_BRACKET:
                bracket_counter -= 1
                if bracket_counter < 0:
                    raise ConfigError(f"Invalid expression (closing bracket without opening bracket) {token.token}")

            prev_token = tokens[i-1] if i > 0 else None
            prev_token_id = prev_token.token_type.value.id if prev_token else 0
            if prev_token_id not in token.token_type.value.prev:
                raise ConfigError(f"Invalid token order (token {token.token} cannot follow token {prev_token.token if prev_token else "BEGIN"})")

        if len(tokens) > 0:
            last_token = tokens[-1]
            if last_token.token_type.value.id not in DAQEquationTokenType.END.value.prev:
                raise ConfigError(f"Invalid token order (token {last_token.token} cannot be the last token in the expression)")

        if bracket_counter != 0:
            raise ConfigError(f"Invalid expression (unclosed brackets)")

    def integrate_unary_minusplus(self, tokens: list[DAQEquationToken]) -> list[DAQEquationToken]:
        new_tokens: list[DAQEquationToken] = []
        for i, token in enumerate(tokens):
            new_tokens.append(token)
            if token.token_type != DAQEquationTokenType.FLOAT:
                continue
            # Unary operators cannot have spaces between the number and operator
            if token.begins_with_whitespace:
                continue

            # Unary operators can only happen at the start, after an operator or after "("
            prev_prev_token = tokens[i-2] if i > 1 else None
            if prev_prev_token and prev_prev_token.token_type != DAQEquationTokenType.OPERATOR and prev_prev_token.token_type != DAQEquationTokenType.OPENING_BRACKET:
                continue

            # Is there a possibly unary operatoe before the float?
            prev_token = tokens[i-1] if i > 0 else None
            if not prev_token or prev_token.token_type != DAQEquationTokenType.OPERATOR or prev_token.token not in UNARY_OPERATORS:
                continue

            # If the previous token is a unary operator, we need to merge it with the float
            _ = new_tokens.pop() # Remove the float now at the top of new_tokens
            # Replace the float token with one with the operator
            new_token = DAQEquationToken(token=prev_token.token + token.token, token_type=DAQEquationTokenType.FLOAT, begin=prev_token.begin, end=token.end, begins_with_whitespace=False)
            new_token.validate()
            new_tokens[-1] = new_token
        return new_tokens

    def tokenize(self, src: str) -> list[DAQEquationToken]:
        tokens: list[DAQEquationToken] = []

        current_token_begin: int = 0
        current_token_str: str = ""
        current_token_match_type: int = 0
        current_token_beings_with_whitespace: bool = False
        current_token_type: DAQEquationTokenType = DAQEquationTokenType.UNKNOWN

        def push_token_validate(token: DAQEquationToken) -> None:
            token.validate()
            tokens.append(token)

        def push_current_token(*, pos: int, push_also: str = "", token_type: DAQEquationTokenType = DAQEquationTokenType.UNKNOWN):
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

        def push_if_not_type(token_match_type: int, pos: int, token_type: DAQEquationTokenType = DAQEquationTokenType.UNKNOWN) -> None:
            nonlocal current_token_match_type
            nonlocal current_token_type
            if current_token_match_type != token_match_type:
                push_current_token(pos=pos, token_type=token_type)
            current_token_type = token_type
            current_token_match_type = token_match_type

        for i, c in enumerate(src.lower()):
            if c == "*":
                if current_token_str != "*" and current_token_str:
                    push_current_token(token_type=DAQEquationTokenType.OPERATOR, pos=i)
                current_token_type = DAQEquationTokenType.OPERATOR
                current_token_str += c
                if current_token_str == "**":
                    push_current_token(pos=i)
            elif c in OPERATORS:
                if c in UNARY_OPERATORS and current_token_match_type == 1 and current_token_str[-1] == 'e':
                    current_token_str += c
                    continue
                push_current_token(push_also=c, token_type=DAQEquationTokenType.OPERATOR, pos=i)
            elif c == "(":
                push_current_token(push_also=c, token_type=DAQEquationTokenType.OPENING_BRACKET, pos=i)
            elif c == ")":
                push_current_token(push_also=c, token_type=DAQEquationTokenType.CLOSING_BRACKET, pos=i)
            elif c in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."):
                ttype = DAQEquationTokenType.FLOAT
                if current_token_str and current_token_str[0] == "c":
                    ttype = DAQEquationTokenType.CHANNEL
                    if len(current_token_str) == 1:
                        current_token_match_type = 1 # Channels start with C and are followed by a number
                push_if_not_type(1, token_type=ttype, pos=i)
                current_token_str += c
            elif c == " ":
                push_current_token(pos=i)
                current_token_beings_with_whitespace = True
            else:
                if c == "e" and current_token_match_type == 1:
                    current_token_str += c
                    continue

                push_if_not_type(2, token_type=DAQEquationTokenType.FUNCTION, pos=i)
                current_token_str += c

        push_current_token(pos=len(src))

        return tokens
