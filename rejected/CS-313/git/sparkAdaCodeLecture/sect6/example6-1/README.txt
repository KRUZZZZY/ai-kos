This code doesn't pass overflow checks but otherwise is okay.

gnatmake example.adb 
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  succeeds
gnatprove -P main.gpr --proof=progressive
  reports possible overflow problems 


example.adb:6:51: medium: overflow check might fail
    6 |      pragma Loop_Invariant (M + N = M'Loop_Entry + N'Loop_Entry);
      |                                     ~~~~~~~~~~~~~^~~~~~~~~~~~~~
  reason for check: result of addition must fit in a 32-bits machine integer

example.adb:7:17: medium: overflow check might fail
    7 |         M := M - 1;
      |              ~~^~~
  reason for check: result of subtraction must fit in a 32-bits machine integer

example.adb:8:17: medium: overflow check might fail
    8 |         N := N + 1;
      |              ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
