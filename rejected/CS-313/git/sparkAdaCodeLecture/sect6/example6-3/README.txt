This code succeeds except for possible overflow problems.

gnatmake test.adb
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr  --proof=progressive
  succeeds
gnatprove -P main.gpr --proof=progressive
  reports a possible overflow problem

test.adb:14:13: medium: overflow check might fail
   14 |      A:= A + 2;
      |          ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at test.ads:13 should mention A in a precondition
   13 |   procedure Procedure1
      |   ^ here
