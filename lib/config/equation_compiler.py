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

OPERATORS = ["+", "-", "*", "^", "**", "/", "(", ")"]
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
            if not self.token[0] == "c" and not self.token[1:].isdigit():
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

class DAQEQuationCompiler:
    def __init__(self) -> None:
        super().__init__()

    def compile(self, src: str) -> DAQEquation | None:
        tokens: list[DAQEquationToken] = []

        current_token_begin: int = 0
        current_token_str: str = ""
        current_token_match_type: int = 0
        current_token_type: DAWEquationTokenType = DAWEquationTokenType.UNKNOWN
        def push_current_token(*, pos: int, push_also: str = "", token_type: DAWEquationTokenType = DAWEquationTokenType.UNKNOWN):
            nonlocal current_token_str
            nonlocal current_token_match_type
            nonlocal current_token_type
            nonlocal current_token_begin
            if current_token_str:
                tokens.append(DAQEquationToken(token=current_token_str, token_type=current_token_type, begin=current_token_begin, end=pos-1))
                current_token_str = ""
                current_token_type = token_type
                current_token_match_type = 0      
            current_token_begin = pos          
            if push_also:
                tokens.append(DAQEquationToken(token=push_also, token_type=token_type, begin=pos, end=pos))

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
            elif c in ("+", "-", "/", "(", ")", "^"):
                push_current_token(push_also=c, token_type=DAWEquationTokenType.OPERATOR, pos=i)
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

        for t in tokens:
            t.validate()
            print(t)
