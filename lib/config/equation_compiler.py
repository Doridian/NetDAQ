from dataclasses import dataclass, field
from enum import Enum
from math import exp, log, log10, sqrt, fabs, trunc
from typing import override

from .equation import DAQEquation


@dataclass(frozen=True, kw_only=True)
class DAQEquationTokenTypeDC:
    id: int
    prev: list[int]


class DAQEquationTokenType(Enum):
    UNKNOWN = DAQEquationTokenTypeDC(id=0, prev=[])
    CHANNEL = DAQEquationTokenTypeDC(id=1, prev=[0, 2, 5, 7, 100])
    OPERATOR = DAQEquationTokenTypeDC(id=2, prev=[1, 4, 6])
    FUNCTION = DAQEquationTokenTypeDC(id=3, prev=[0, 2, 5, 7, 100])
    FLOAT = DAQEquationTokenTypeDC(id=4, prev=[0, 2, 5, 7, 100])
    OPENING_BRACKET = DAQEquationTokenTypeDC(id=5, prev=[0, 2, 3, 5, 7, 100])
    CLOSING_BRACKET = DAQEquationTokenTypeDC(id=6, prev=[1, 4, 6])
    UNARY_OPERATOR = DAQEquationTokenTypeDC(id=7, prev=[0, 1, 2, 4, 6, 7, 100])

    BEGIN = DAQEquationTokenTypeDC(id=100, prev=[])
    END = DAQEquationTokenTypeDC(id=101, prev=[1, 4, 6])


UNARY_OPERATORS = ["+", "-"]
OPERATORS = ["*", "^", "**", "/"]  # ^ == **
COMMUTATIVE_OPERATORS = ["+", "*"]
FUNCTIONS = ["exp", "ln", "log", "abs", "int", "sqrt"]  # log == log10
DIGITS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."]
DIGIT_ALLOWED_MIDDLE = ["e", "f", "d"]

OPTERATOR_PRECEDENCE = (
    {  # Keep these 1000 apart, we nudge them for optimization reasons
        "+": 1000,
        "-": 1000,
        "*": 2000,
        "/": 2000,
        "^": 3000,
        "**": 3000,
    }
)


@dataclass(frozen=True, kw_only=True)
class DAQEquationToken:
    token: str
    token_type: DAQEquationTokenType
    begin: int
    end: int
    begins_with_whitespace: bool

    @override
    def __repr__(self) -> str:
        return f'"{self.token}" @ {self.begin}-{self.end}'

    def validate(self) -> None:
        if self.token_type == DAQEquationTokenType.UNKNOWN:
            raise DAQTokenError("Unknown token type for token", self)
        elif self.token_type == DAQEquationTokenType.CHANNEL:
            channel_token = self.token
            if channel_token[0] == "-":
                channel_token = channel_token[1:]

            if channel_token[0] != "c":
                raise DAQTokenError(
                    "Invalid channel token (does not begin with c)", self
                )
            try:
                n = int(channel_token[1:])
                if n <= 0:
                    raise DAQTokenError(
                        "Invalid channel token (channel number must be greater than 0)",
                        self,
                    )
            except ValueError:
                raise DAQTokenError("Invalid channel token", self)
        elif self.token_type == DAQEquationTokenType.FLOAT:
            float_token = self.token
            if float_token[-1] == "f" or float_token[-1] == "d":
                float_token = float_token[:-1]

            try:
                _ = float(float_token)
            except ValueError:
                raise DAQTokenError("Invalid float token", self)
        elif self.token_type == DAQEquationTokenType.OPERATOR:
            if self.token not in OPERATORS:
                raise DAQTokenError("Invalid operator token", self)
        elif self.token_type == DAQEquationTokenType.UNARY_OPERATOR:
            if self.token not in UNARY_OPERATORS:
                raise DAQTokenError("Invalid maybe-unary operator token", self)
        elif self.token_type == DAQEquationTokenType.FUNCTION:
            func_token = self.token
            if func_token[0] == "-":
                func_token = func_token[1:]
            if func_token not in FUNCTIONS:
                raise DAQTokenError("Invalid function token", self)


@dataclass
class DAQEquationTokenTreeNode:
    nodes: list["DAQEquationTokenTreeNode"] = field(default_factory=lambda: [])
    value: DAQEquationToken | None = None

    @staticmethod
    def _emit_token(token: DAQEquationToken, eq: DAQEquation) -> None:
        if token.token_type == DAQEquationTokenType.CHANNEL:
            channel_token = token.token
            do_negate = channel_token[0] == "-"
            if do_negate:
                channel_token = channel_token[1:]

            _ = eq.push_channel(int(channel_token[1:]))

            if do_negate:
                _ = eq.unary_minus()
        elif token.token_type == DAQEquationTokenType.FLOAT:
            token_str = token.token
            is_double = False
            if token_str[-1] == "f":
                token_str = token_str[:-1]
            elif token_str[-1] == "d":
                token_str = token_str[:-1]
                is_double = True

            token_val = float(token_str)
            if is_double:
                _ = eq.push_double(token_val)
            else:
                _ = eq.push_float(token_val)
        elif (
            token.token_type == DAQEquationTokenType.OPERATOR
            or token.token_type == DAQEquationTokenType.UNARY_OPERATOR
        ):
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
            else:
                raise DAQTokenError("Unhandled operator token for emit", token)

        elif token.token_type == DAQEquationTokenType.FUNCTION:
            func_token = token.token
            do_negate = func_token[0] == "-"
            if do_negate:
                func_token = func_token[1:]

            if func_token == "exp":
                _ = eq.exp()
            elif func_token == "ln":
                _ = eq.ln()
            elif func_token == "log":
                _ = eq.log()
            elif func_token == "abs":
                _ = eq.abs()
            elif func_token == "int":
                _ = eq.int()
            elif func_token == "sqrt":
                _ = eq.sqrt()
            else:
                raise DAQTokenError("Unhandled function token for emit", token)

            if do_negate:
                _ = eq.unary_minus()

    def emit(self, eq: DAQEquation) -> None:
        old_stack_depth = eq.get_stack_depth()

        if len(self.nodes) == 1:
            self.nodes[0].emit(eq)
        elif len(self.nodes) == 2:
            if self.nodes[0].value is None:
                raise DAQTreeError(
                    "Invalid token tree (missing unary operator node value)", self
                )

            self.nodes[1].emit(eq)
            self._emit_token(self.nodes[0].value, eq)
        elif len(self.nodes) == 3:
            if self.nodes[1].value is None:
                raise DAQTreeError(
                    f"Invalid token tree (missing binary operator node value)",
                    self,
                )

            # Reorder nodes to minimize stack usage
            eq_a = DAQEquation()
            self.nodes[0].emit(eq_a)
            assert eq_a.get_stack_depth() == 1

            eq_b = DAQEquation()
            self.nodes[2].emit(eq_b)
            assert eq_b.get_stack_depth() == 1

            operator = self.nodes[1].value
            if operator.token in COMMUTATIVE_OPERATORS and eq_a.get_max_stack_depth() < eq_b.get_max_stack_depth():
                eq.append(eq_b)
                eq.append(eq_a)
            else:
                eq.append(eq_a)
                eq.append(eq_b)

            self._emit_token(operator, eq)

        if self.value:
            self._emit_token(self.value, eq)

        assert eq.get_stack_depth() == old_stack_depth + 1

    def resolve_constant_expression(self) -> None:
        for node in self.nodes:
            node.resolve_constant_expression()

        if len(self.nodes) == 1:
            sub_node = self.nodes[0]
            if not self.value:
                self.value = sub_node.value
                self.nodes = sub_node.nodes
                return

            if (
                not sub_node.value
            ) or sub_node.value.token_type != DAQEquationTokenType.FLOAT:
                return

            if (
                not self.value
            ) or self.value.token_type != DAQEquationTokenType.FUNCTION:
                raise DAQTokenError("Invalid constant expression", self.value)

            func_token = self.value.token
            do_negate = func_token[0] == "-"
            if do_negate:
                func_token = func_token[1:]

            token_value = float(sub_node.value.token)
            if func_token == "exp":
                token_value = exp(token_value)
            elif func_token == "ln":
                token_value = log(token_value)
            elif func_token == "log":
                token_value = log10(token_value)
            elif func_token == "abs":
                token_value = fabs(token_value)
            elif func_token == "int":
                token_value = float(trunc(token_value))
            elif func_token == "sqrt":
                token_value = sqrt(token_value)
            else:
                raise DAQTokenError(
                    "Unhandled function token for constant expression", self.value
                )

            if do_negate:
                token_value = -token_value

            self.value = self.nodes[0].value
            self.nodes = []

        if len(self.nodes) != 3:
            return

        node_left = self.nodes[0]
        node_right = self.nodes[2]
        if (
            node_left.value
            and node_left.value.token_type == DAQEquationTokenType.FLOAT
            and node_right.value
            and node_right.value.token_type == DAQEquationTokenType.FLOAT
        ):
            value_left = float(node_left.value.token)
            value_right = float(node_right.value.token)
            new_float_value = 0.0
            op = self.nodes[1].value

            if not op:
                raise DAQMissingTokenError("Operator token for constant expression")
            if (
                op.token_type != DAQEquationTokenType.OPERATOR
                and op.token_type != DAQEquationTokenType.UNARY_OPERATOR
            ):
                raise DAQTokenError(
                    "Invalid operator token for constant expression", op
                )

            if op.token == "+":
                new_float_value = value_left + value_right
            elif op.token == "-":
                new_float_value = value_left - value_right
            elif op.token == "*":
                new_float_value = value_left * value_right
            elif op.token == "/":
                new_float_value = value_left / value_right
            elif op.token == "^" or op.token == "**":
                new_float_value = value_left**value_right
            else:
                raise DAQTokenError(
                    "Unhandled operator token for constant expression", op
                )

            self.value = DAQEquationToken(
                token=str(new_float_value),
                token_type=DAQEquationTokenType.FLOAT,
                begin=node_left.value.begin,
                end=node_right.value.end,
                begins_with_whitespace=False,
            )
            self.nodes = []

    # Turn tree into only subtrees of the form "X" or "X", <OP>, "Y"
    def simplify_token_tree(self) -> None:
        for node in self.nodes:
            node.simplify_token_tree()

        self._simplify_token_tree_shallow()

    def _simplify_token_tree_shallow(
        self
    ) -> None:
        if len(self.nodes) == 1 and not self.value:
            self.value = self.nodes[0].value
            self.nodes = self.nodes[0].nodes
            return

        # 1-3 node subtrees cannot be simplified
        if len(self.nodes) < 4:
            return

        # We must now be in a leaf node of the form "X", <OP>, "Y", <OP>, "Z", ...
        best_operator: int | None = None
        best_operator_precedence: int = 0
        for i, sub_node in enumerate(self.nodes):
            if not sub_node.value or (
                sub_node.value.token_type != DAQEquationTokenType.OPERATOR
                and sub_node.value.token_type != DAQEquationTokenType.UNARY_OPERATOR
            ):
                continue

            this_operator_precedence = OPTERATOR_PRECEDENCE[sub_node.value.token]

            # Deprioritize operators that operate on constants
            # This will force the tree shaker to optimize away all possible constant expressions
            prev_token = self.nodes[i - 1].value if i > 0 else None
            if prev_token and prev_token.token_type == DAQEquationTokenType.FLOAT:
                this_operator_precedence -= 1
            next_token = (
                self.nodes[i + 1].value if i + 1 < len(self.nodes) else None
            )
            if next_token and next_token.token_type == DAQEquationTokenType.FLOAT:
                this_operator_precedence -= 1

            if this_operator_precedence < best_operator_precedence:
                continue
            best_operator = i
            best_operator_precedence = this_operator_precedence

        if best_operator is None:
            raise DAQTreeError(f"Invalid token tree (no operators found)", self)

        new_tree_left = DAQEquationTokenTreeNode(nodes=self.nodes[:best_operator])
        new_tree_op = DAQEquationTokenTreeNode(
            value=self.nodes[best_operator].value
        )
        new_tree_right = DAQEquationTokenTreeNode(
            nodes=self.nodes[best_operator + 1 :]
        )

        new_tree_left._simplify_token_tree_shallow()
        new_tree_right._simplify_token_tree_shallow()

        self.nodes = [
            new_tree_left,
            new_tree_op,
            new_tree_right,
        ]

    @override
    def __repr__(self) -> str:
        return self.repr_with_indent()

    def repr_with_indent(self, indent: str = "") -> str:
        res = f"{indent}DAQEquationTokenTreeNode("
        sub_indent = indent + '  '

        if self.value:
            res +=  f"value=\"{self.value.token}\""

        if self.nodes:
            if self.value:
                res += ", "
            res += "nodes=[\n"
            for node in self.nodes:
                res += node.repr_with_indent(sub_indent + '  ') + ",\n"
            res += f"{indent}]"

        return res + ")"

class ParseError(Exception):
    pass


class DAQTreeError(ParseError):
    token_tree: DAQEquationTokenTreeNode
    raw_msg: str

    def __init__(self, msg: str, token_tree: DAQEquationTokenTreeNode) -> None:
        super().__init__(f"{msg} {token_tree}")
        self.token_tree = token_tree
        self.raw_msg = msg


class DAQTokenError(ParseError):
    token: DAQEquationToken
    raw_msg: str

    def __init__(self, msg: str, token: DAQEquationToken) -> None:
        super().__init__(f"{msg} {token}")
        self.token = token
        self.raw_msg = msg


class DAQMultiTokenError(ParseError):
    tokens: list[DAQEquationToken]
    raw_msg: str

    def __init__(self, msg: str, tokens: list[DAQEquationToken]) -> None:
        super().__init__(f"{msg} {tokens}")
        self.tokens = tokens
        self.raw_msg = msg


class DAQMissingTokenError(ParseError):
    raw_msg: str

    def __init__(self, msg: str) -> None:
        super().__init__(f"{msg} (missing token)")
        self.raw_msg = msg


class DAQEQuationCompiler:
    def __init__(self) -> None:
        super().__init__()

    def compile(self, src: str) -> DAQEquation | None:
        tokens = self.tokenize(src)
        tokens = self.integrate_unary_minusplus(tokens)
        self.validate_token_order(tokens)

        token_tree = self.build_token_tree(tokens.copy())
        token_tree.simplify_token_tree()
        token_tree.resolve_constant_expression()

        print(token_tree)

        eq = DAQEquation()
        token_tree.emit(eq)
        _ = eq.end()
        eq.validate()

        return eq

    def build_token_tree(
        self, tokens: list[DAQEquationToken], *, value: DAQEquationToken | None = None
    ) -> DAQEquationTokenTreeNode:
        token_tree = DAQEquationTokenTreeNode(value=value)

        while tokens:
            token = tokens.pop(0)
            if token.token_type == DAQEquationTokenType.FUNCTION:
                token_must_be_bracket = tokens.pop(0)
                if (
                    (not token_must_be_bracket)
                    or token_must_be_bracket.token_type
                    != DAQEquationTokenType.OPENING_BRACKET
                ):
                    raise DAQMultiTokenError(
                        "Invalid expression (function must be followed by an opening bracket)",
                        tokens=[token, token_must_be_bracket],
                    )
                token_tree.nodes.append(self.build_token_tree(tokens, value=token))
                continue
            if token.token_type == DAQEquationTokenType.OPENING_BRACKET:
                token_tree.nodes.append(self.build_token_tree(tokens))
                continue
            elif token.token_type == DAQEquationTokenType.CLOSING_BRACKET:
                break
            token_tree.nodes.append(DAQEquationTokenTreeNode(value=token))

        if len(token_tree.nodes) == 0:
            raise DAQTreeError("Invalid expression (empty tree)", token_tree)
        # Just return single child node if this is a bare bracket (no function)
        elif len(token_tree.nodes) == 1 and token_tree.value is None:
            return token_tree.nodes[0]

        return token_tree

    def validate_token_order(self, tokens: list[DAQEquationToken]) -> None:
        if not tokens:
            return

        bracket_counter: int = 0

        for i in range(len(tokens) + 1):
            if i == len(tokens):
                last_token_end = tokens[-1].end
                token = DAQEquationToken(
                    token="",
                    token_type=DAQEquationTokenType.END,
                    begin=last_token_end,
                    end=last_token_end,
                    begins_with_whitespace=False,
                )
            else:
                token = tokens[i]

            if i == 0:
                prev_token = DAQEquationToken(
                    token="",
                    token_type=DAQEquationTokenType.BEGIN,
                    begin=0,
                    end=0,
                    begins_with_whitespace=False,
                )
            else:
                prev_token = tokens[i - 1]

            if token.token_type == DAQEquationTokenType.OPENING_BRACKET:
                bracket_counter += 1
            elif token.token_type == DAQEquationTokenType.CLOSING_BRACKET:
                bracket_counter -= 1
                if bracket_counter < 0:
                    raise DAQTokenError(
                        "Invalid expression (closing bracket without opening bracket)",
                        token,
                    )

            if prev_token.token_type.value.id not in token.token_type.value.prev:
                raise DAQMultiTokenError(
                    f"Invalid token order (token cannot follow token)",
                    tokens=[prev_token, token],
                )

        if bracket_counter != 0:
            raise DAQMultiTokenError(
                f"Invalid expression (unclosed brackets)", tokens=tokens
            )

    def integrate_unary_minusplus(
        self, tokens: list[DAQEquationToken]
    ) -> list[DAQEquationToken]:
        new_tokens: list[DAQEquationToken] = []

        first_unary_token: int = -1
        for i, token in enumerate(tokens):
            if token.token_type == DAQEquationTokenType.UNARY_OPERATOR:
                if first_unary_token < 0:
                    # Unary operators can only happen at the start, after an operator or after "("
                    prev_token = tokens[i - 1] if i > 0 else None
                    if (
                        prev_token
                        and prev_token.token_type != DAQEquationTokenType.OPERATOR
                        and prev_token.token_type != DAQEquationTokenType.UNARY_OPERATOR
                        and prev_token.token_type
                        != DAQEquationTokenType.OPENING_BRACKET
                    ):
                        new_tokens.append(token)
                        continue
                    first_unary_token = i
                    continue
                if token.begins_with_whitespace:
                    raise DAQMultiTokenError(
                        f"Invalid expression (unary operator chain cannot have whitespace inside of it)",
                        tokens=tokens[first_unary_token : i + 1],
                    )
                continue

            # Unary operators cannot have spaces between the token and operator
            if token.begins_with_whitespace:
                new_tokens.append(token)
                first_unary_token = -1
                continue

            if first_unary_token < 0:
                new_tokens.append(token)
                continue

            all_unary_tokens = tokens[first_unary_token:i]
            minus_count = 0
            for unary_token in all_unary_tokens:
                if unary_token.token == "-":
                    minus_count += 1

            new_token_value = token.token
            if minus_count % 2 == 1:
                if new_token_value[0] == "-":
                    new_token_value = new_token_value[1:]
                else:
                    new_token_value = "-" + new_token_value

            new_token = DAQEquationToken(
                token=new_token_value,
                token_type=token.token_type,
                begin=tokens[first_unary_token].begin,
                end=token.end,
                begins_with_whitespace=False,
            )
            new_token.validate()
            new_tokens.append(new_token)
            first_unary_token = -1

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

        def push_current_token(
            *,
            pos: int,
            push_also: str = "",
            token_type: DAQEquationTokenType = DAQEquationTokenType.UNKNOWN,
        ):
            nonlocal current_token_str
            nonlocal current_token_match_type
            nonlocal current_token_type
            nonlocal current_token_begin
            nonlocal current_token_beings_with_whitespace
            if current_token_str:
                push_token_validate(
                    DAQEquationToken(
                        token=current_token_str,
                        token_type=current_token_type,
                        begin=current_token_begin,
                        end=pos - 1,
                        begins_with_whitespace=current_token_beings_with_whitespace,
                    )
                )
                current_token_str = ""
                current_token_type = token_type
                current_token_match_type = 0
                current_token_beings_with_whitespace = False
            current_token_begin = pos
            if push_also:
                push_token_validate(
                    DAQEquationToken(
                        token=push_also,
                        token_type=token_type,
                        begin=pos,
                        end=pos,
                        begins_with_whitespace=current_token_beings_with_whitespace,
                    )
                )
                current_token_beings_with_whitespace = False

        def push_if_not_type(
            token_match_type: int,
            pos: int,
            token_type: DAQEquationTokenType = DAQEquationTokenType.UNKNOWN,
        ) -> None:
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
            elif c in UNARY_OPERATORS:
                if current_token_match_type == 1 and current_token_str[-1] == "e":
                    current_token_str += c
                    continue
                push_current_token(
                    push_also=c, token_type=DAQEquationTokenType.UNARY_OPERATOR, pos=i
                )
            elif c in OPERATORS:
                push_current_token(
                    push_also=c, token_type=DAQEquationTokenType.OPERATOR, pos=i
                )
            elif c == "(":
                push_current_token(
                    push_also=c, token_type=DAQEquationTokenType.OPENING_BRACKET, pos=i
                )
            elif c == ")":
                push_current_token(
                    push_also=c, token_type=DAQEquationTokenType.CLOSING_BRACKET, pos=i
                )
            elif c in DIGITS:
                ttype = DAQEquationTokenType.FLOAT
                if current_token_str and current_token_str[0] == "c":
                    ttype = DAQEquationTokenType.CHANNEL
                    if len(current_token_str) == 1:
                        current_token_match_type = (
                            1  # Channels start with C and are followed by a number
                        )
                push_if_not_type(1, token_type=ttype, pos=i)
                current_token_str += c
            elif c == " ":
                push_current_token(pos=i)
                current_token_beings_with_whitespace = True
            else:
                if current_token_match_type == 1 and c in DIGIT_ALLOWED_MIDDLE:
                    current_token_str += c
                    continue

                push_if_not_type(2, token_type=DAQEquationTokenType.FUNCTION, pos=i)
                current_token_str += c

        push_current_token(pos=len(src))

        return tokens
