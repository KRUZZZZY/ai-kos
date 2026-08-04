Program okay except for overlow checks

gnatmake test.adb
 succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
 succeeds


gnatprove -P main.gpr --proof=progressive
  reports a possible overflow problem

test.adb:7:18: medium: overflow check might fail
    7 |   else return X + 1;
      |               ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
