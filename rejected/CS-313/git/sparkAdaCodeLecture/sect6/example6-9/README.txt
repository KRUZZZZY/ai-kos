Program okay except for overflow checks

gnatmake test.adb
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  succeeds
gnatprove -P main.gpr --proof=progressive
  reports a possible overflow problem

test.adb:5:13: medium: overflow check might fail
    5 |   return X + 1;
      |          ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
