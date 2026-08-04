Program okay except for overflow checks

gnatmake test.adb
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr  --proof=progressive
  succeeds
gnatprove -P main.gpr --proof=progressive
  reports possible overflow problem

test.adb:6:49: medium: overflow check might fail
    6 |   function F(X : Integer) return Integer is (X + 1);
      |                                             ~~~^~~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at test.ads:5 should mention X in a precondition
    5 |   function F(X : Integer) return Integer;
      |   ^ here


