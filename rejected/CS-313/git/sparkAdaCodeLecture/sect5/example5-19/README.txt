See as well example5-14, example5-18, example5-20

This example demonstrates that after an assert and cut all previous verification
conditions are lost.
While the post condition always hold for all inputs, it is not provable because after
the assert and cut all SPARK Ada knows is that  U = X +1 where X is not X'Old but the one
at that point. So it doesn't know anything about U vs X'Old and therefore cannot
show the postcondition.

gnatmake test.adb
 succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
 reports

test.ads:4:16: medium: postcondition might fail
    4 |       Post => (X  = X'Old + 3);
      |               ^~~~~~~~~~~~~~~~

