This example demonstrates the syntax of verification conditions
  but the verification conditions are not passed.

gnatmake example.adb
  succeeds
gnatprove -P main.gpr --mode=flow
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
 gives error
example.ads:13:11: medium: postcondition might fail
   13 |  Post => M = M'Old + 1;
      |          ^~~~~~~~~~~~~


gnatprove -P main.gpr --proof=progressive
  gives in addition various possible overflow problems.
