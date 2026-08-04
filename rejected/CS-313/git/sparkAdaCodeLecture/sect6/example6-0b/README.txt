This example demonstrates that the number of created verification conditions
  is big if using assert instead of assert_and_cut
This code doesn't pass overflow checks but otherwise is okay.


gnatmake test.adb
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  succeeds
gnatprove -P main.gpr --proof=progressive
  reports possible overflow problems:

test.adb:6:16: medium: overflow check might fail
    6 |   then X := X + 1;
      |             ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer

test.adb:10:16: medium: overflow check might fail
   10 |   then X := X + 1;
      |             ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer

test.adb:14:16: medium: overflow check might fail
   14 |   then X := X + 1;
      |             ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer




