This is an example as discussed in the lecture that without a loop invariant one usually
  cannot prove the post condition.
The system cannot prove the post condition.

gnatmake example.adb
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
fails:

example.ads:7:12: medium: postcondition might fail, cannot prove M + N = M'Old + N'old
    7 |  Post => (M + N = M'Old + N'Old and M < 0);
      |           ^~~~~~~~~~~~~~~~~~~~~

gnatprove -P main.gpr --proof=progressive
shows in addition several possible overflow  problems
