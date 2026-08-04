gnatmake loop_entry.adb
 succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
 succeeds
gnatprove -P main.gpr --proof=progressive
 reports possible overflow problems:


loop_entry.adb:11:17: medium: overflow check might fail
   11 |         B := B + 1;
      |              ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer

loop_entry.adb:12:46: medium: overflow check might fail
   12 |         pragma Loop_Invariant (A + B = Aold + Bold);
      |                                        ~~~~~^~~~~~
  reason for check: result of addition must fit in a 32-bits machine integer

loop_entry.ads:7:28: medium: overflow check might fail
    7 |    Post => (A + B = A'Old + B'Old);
      |                     ~~~~~~^~~~~~~
