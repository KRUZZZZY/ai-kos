This code succeeds except for a possible overflow problem.

gnatmake test.adb
  succeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  succeds
gnatprove -P main.gpr --proof=progressive
  reports a possible overflow problem:


test.adb:14:13: medium: overflow check might fail
   14 |      A:= A + 2;
      |          ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at test.ads:10 should mention A in a precondition
   10 |   procedure Inc2(A : in out Integer)
      |   ^ here

