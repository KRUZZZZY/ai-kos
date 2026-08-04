This program succeeds except for overflow checks

gnatmake test.adb
 succeeds
gnatprove -P mainWithoutRangeCheck.gpr  --proof=progressive
 succeeds

gnatprove -P main.gpr --proof=progressive
  reports possible overflow problem

test.adb:14:13: medium: overflow check might fail
   14 |      A:= A + 2;
      |          ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
