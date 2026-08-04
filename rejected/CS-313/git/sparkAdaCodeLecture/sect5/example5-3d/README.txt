Example to demonstrate syntax of verification conditions.
It doesn't intend to pass the verification and indeed doesn't

gnatmake example.adb
  succeeds
gnatprove -P main.gpr --mode=flow
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  fails with error

example.ads:15:46: medium: postcondition might fail, cannot prove M = M'Old + 1
   15 |  Post => (for all X in Integer => X = X and M = M'Old + 1);
      |                                             ^~~~~~~~~~~~~
