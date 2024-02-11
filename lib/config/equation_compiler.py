from dataclasses import dataclass
from enum import Enum

from .equation import DAQEquation
from .base import ConfigError

class DAWEquationTokenType(Enum):
    UNKNOWN = 0
    CHANNEL = 1
    OPERATOR = 2
    FUNCTION = 3
    FLOAT = 4
    BRACKET = 5

BRACKETS = ["(", ")"]
UNARY_OPERATORS = ["+", "-"]
OPERATORS = ["+", "-", "*", "^", "**", "/"]
FUNCTIONS = ["exp", "ln", "log", "abs", "int", "sqrt"]

@dataclass(frozen=True, kw_only=True)
class DAQEquationToken:
    token: str
    token_type: DAWEquationTokenType
    begin: int
    end: int

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
        elif self.token_type == DAWEquationTokenType.BRACKET:    
            if self.token not in BRACKETS:
                raise ConfigError(f"Invalid bracket token {self.token}")
        elif self.token_type == DAWEquationTokenType.FUNCTION:
            if self.token not in FUNCTIONS:
                raise ConfigError(f"Invalid function token {self.token}")

class DAQEQuationCompiler:
    def __init__(self) -> None:
        super().__init__()

    def compile(self, src: str) -> DAQEquation | None:
        pass

    def integrate_unary_minusplus(self, tokens: list[DAQEquationToken]) -> list[DAQEquationToken]:
        new_tokens: list[DAQEquationToken] = []
        for i, token in enumerate(tokens):
            new_tokens.append(token)
            if token.token_type != DAWEquationTokenType.FLOAT:
                continue

            # Unary operators can only happen at the start, after an operator or after "("
            prev_prev_token = tokens[i-2] if i > 1 else None
            if prev_prev_token and prev_prev_token.token_type != DAWEquationTokenType.OPERATOR and (prev_prev_token.token_type != DAWEquationTokenType.BRACKET or prev_prev_token.token != "("):
                continue

            # Is there a possibly unary operatoe before the float?
            prev_token = tokens[i-1] if i > 0 else None
            if not prev_token or prev_token.token_type != DAWEquationTokenType.OPERATOR or prev_token.token not in UNARY_OPERATORS:
                continue

            # If the previous token is a unary operator, we need to merge it with the float
            _ = new_tokens.pop() # Remove the float now at the top of new_tokens
            # Replace the float token with one with the operator
            new_tokens[-1] = DAQEquationToken(token=prev_token.token + token.token, token_type=DAWEquationTokenType.FLOAT, begin=prev_token.begin, end=token.end)
            

    def tokenize(self, src: str) -> list[DAQEquationToken]:
        tokens: list[DAQEquationToken] = []

        current_token_begin: int = 0
        current_token_str: str = ""
        current_token_match_type: int = 0
        current_token_type: DAWEquationTokenType = DAWEquationTokenType.UNKNOWN

        def push_token_validate(token: DAQEquationToken) -> None:
            token.validate()
            tokens.append(token)

        def push_current_token(*, pos: int, push_also: str = "", token_type: DAWEquationTokenType = DAWEquationTokenType.UNKNOWN):
            nonlocal current_token_str
            nonlocal current_token_match_type
            nonlocal current_token_type
            nonlocal current_token_begin
            if current_token_str:
                push_token_validate(DAQEquationToken(token=current_token_str, token_type=current_token_type, begin=current_token_begin, end=pos-1))
                current_token_str = ""
                current_token_type = token_type
                current_token_match_type = 0      
            current_token_begin = pos          
            if push_also:
                push_token_validate(DAQEquationToken(token=push_also, token_type=token_type, begin=pos, end=pos))

        def push_if_not_type(token_match_type: int, pos: int, token_type: DAWEquationTokenType = DAWEquationTokenType.UNKNOWN) -> None:
            nonlocal current_token_match_type
            nonlocal current_token_type
            if current_token_match_type != token_match_type:
                push_current_token(pos=pos, token_type=token_type)
            current_token_type = token_type
            current_token_match_type = token_match_type

        for i, c in enumerate(src.lower()):
            if c == "*":
                if current_token_str != "*"  and current_token_str:
                    push_current_token(token_type=DAWEquationTokenType.OPERATOR, pos=i)
                current_token_type = DAWEquationTokenType.OPERATOR
                current_token_str += c
                if current_token_str == "**":
                    push_current_token(pos=i)
            elif c in OPERATORS:
                push_current_token(push_also=c, token_type=DAWEquationTokenType.OPERATOR, pos=i)
            elif c in BRACKETS:
                push_current_token(push_also=c, token_type=DAWEquationTokenType.BRACKET, pos=i)
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
            else:
                push_if_not_type(2, token_type=DAWEquationTokenType.FUNCTION, pos=i)
                current_token_str += c

        push_current_token(pos=len(src))

        return tokens
