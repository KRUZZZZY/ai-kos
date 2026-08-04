gnatmake test.adb
 succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
 succeeds
gnatprove -P main.gpr --proof=progressive
 shows possible overflow problem:

test.adb:5:11: medium: overflow check might fail
    5 |   X := X + 1;
      |        ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at test.ads:2 should mention X in a precondition
    2 |procedure Test (X: in out Integer)
      |^ here

test.adb:7:10: medium: overflow check might fail
    7 |   X:= X + 1;
      |       ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at test.ads:2 should mention X in a precondition
    2 |procedure Test (X: in out Integer)
      |^ here
