See as well example5-14, example5-19, example5-20

gnatmake test.adb
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive 
  succeeds
gnatprove -P main.gpr --proof=progressive
 reports possible overflow problems:

test.adb:5:11: medium: overflow check might fail
    5 |   U := U + 1;
      |        ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer

test.adb:7:10: medium: overflow check might fail
    7 |   X:= U + 1;
      |       ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
