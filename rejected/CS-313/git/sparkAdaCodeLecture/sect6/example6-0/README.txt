This file demonstrates that the 
number of created verification conditions beomces much smaller when using assert_and_cut
  instead of assert
Range conditions fail in this example, otherwise it is okay

gnatmake test.adb 
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  succeeds
gnatprove -P main.gpr --proof=progressive
  reports possible overflow problems

test.adb:6:16: medium: overflow check might fail
    6 |   then X := X + 1;
      |             ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer

test.adb:11:16: medium: overflow check might fail
   11 |   then X := X + 1;
      |             ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer

test.adb:16:16: medium: overflow check might fail
   16 |   then X := X + 1;
      |             ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer

