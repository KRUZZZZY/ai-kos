This example is intended to demonstrate the syntax of verification conditions without
  intending to have verified code. It doesn't pass verification conditions.

gnatmake example.adb
  succeeds
gnatprove -P main.gpr --mode=flow
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  fails 
example.ads:12:46: medium: postcondition might fail, cannot prove M = M'Old + 1
   12 |  Post => (for all X in Integer => X = X and M = M'Old + 1);
      |                                             ^~~~~~~~~~~~~

  
