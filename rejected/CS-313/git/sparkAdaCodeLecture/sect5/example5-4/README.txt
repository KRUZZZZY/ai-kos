Example to demonstrate syntax of verification conditions.
It doesn't intend to pass the verification and indeed doesn't


gnatmake example.adb
  succeeds
gnatprove -P main.gpr --mode=flow
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  fails with error

example.ads:11:11: medium: postcondition might fail
   11 |  Post => M = M'Old + 1;
      |          ^~~~~~~~~~~~~
