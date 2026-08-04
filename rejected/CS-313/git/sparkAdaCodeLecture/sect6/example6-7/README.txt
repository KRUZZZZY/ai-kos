gnatmake test.adb
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  succeeds
gnatprove -P main.gpr --proof=progressive
  reports a possible overflow problem

test.adb:8:16: medium: overflow check might fail
    8 |      return A + 3;
      |             ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at test.ads:6 should mention A in a precondition
    6 |   function Myfunction(A : Integer) return Integer
      |   ^ here

 
