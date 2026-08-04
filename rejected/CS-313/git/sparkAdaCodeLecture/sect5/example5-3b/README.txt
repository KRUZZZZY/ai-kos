Example for demonstrating syntax of verification conditions.
This example is not intended to pass verification conditions.

gnatmake example.adb
  succeeds
gnatprove -P main.gpr --mode=flow
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  fails

example.ads:12:45: medium: postcondition might fail, cannot prove M = M'Old + 1
   12 |  Post => (for all X in Mytype => X = X and M = M'Old + 1);
      |                                            ^~~~~~~~~~~~~




