This code doesn't pass overflow checks but otherwise is okay.

gnatmake example.adb 
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  succeeds
gnatprove -P main.gpr --proof=progressive
  reports possible overflow problems 

example.adb:6:51: medium: overflow check might fail
    6 |      pragma Loop_Invariant (M + N = M'Loop_Entry + N'Loop_Entry and M > 0);
      |                                     ~~~~~~~~~~~~~^~~~~~~~~~~~~~
  reason for check: result of addition must fit in a 32-bits machine integer
