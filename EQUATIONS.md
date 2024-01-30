# Equations

## Basic structure

Seems to be a very simple stack-based language

## Examples

```
20*log(C1/C2)
02 41 a0 00 00 01 00 01  01 00 02 08 0c 07 00
02 float-20(4B) 01 channel-1(2B) 01 channel-2(2B) 08 0c 07 00

20*log(C2/C1)
02 41 a0 00 00 01 00 02  01 00 01 08 0c 07 00
02 float-20(4B) 01 channel-2(2B) 01 channel-1(2B) 08 0c 07 00
```

## Opcodes (1 byte + variable immediate)

- 0x00 = end program
- 0x01 = PUSH the value of the following channel (2-byte integer) (`C1`)
- 0x02 = PUSH following 4-byte float immediate (`1.234`)
- 0x03 = ? (unused)
- 0x04 = POP top of stack, PUSH its inverse (`-X`)
- 0x05 = POP and subtract top 2 values on stack (top of stack is RHS), PUSH result (`X-Y`)
- 0x06 = POP and add top 2 values on stack, PUSH result (`X+Y`)
- 0x07 = POP and multiply top 2 values on stack, PUSH result (`X*Y`)
- 0x08 = POP and divide top 2 values on stack (top of stack is RHS/divisor), PUSH result (`X/Y`)
- 0x09 = POP and raise to power top 2 values on stack (top of stack is RHS/exponent), PUSH result (`X^Y`)
- 0x0A = POP top of stack, PUSH e raised to its value (`exp(X)`)
- 0x0B = POP top of stack, PUSH its natural logarithm (`ln(X)`)
- 0x0C = POP top of stack, PUSH its logarithm base 2 (`log(X)`)
- 0x0D = POP top of stack, PUSH its absolute (`abs(X)`)
- 0x0E = POP top of stack, PUSH its value rounded toward zero (`int(X)`)
- 0x0F = POP top of stack, PUSH its square root (`sqr(X)`)
