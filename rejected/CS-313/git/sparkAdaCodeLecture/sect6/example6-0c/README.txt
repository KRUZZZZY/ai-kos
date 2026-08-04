This program compiles using

gnatmake main.adb

When executing it crashes if you enter on the prompt value
2147483647
with error
raised CONSTRAINT_ERROR : main.adb:14 overflow check failed

since 2147483647 is the largest integer, and incrementing
it by 1 results in an overflow error.

Entering a number greater than 2147483647
at the user prompt
causes a crash at the Get(X) statement, since the number is too big:

raised ADA.IO_EXCEPTIONS.DATA_ERROR : a-tiinio.adb:104 instantiated at a-inteio.ads:18
