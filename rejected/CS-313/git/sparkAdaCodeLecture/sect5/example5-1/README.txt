Basic notation for pre and post conditions


gnatmake example.adb
  succeeds

gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  succeeds

gnatprove -P main.gpr --proof=progressive
reports two overflow check condition problems:

example.adb:8:14: medium: overflow check might fail
    8 |      N := N - 1;
      |           ~~^~~
  reason for check: result of subtraction must fit in a 32-bits machine integer

example.adb:9:14: medium: overflow check might fail
    9 |      M := M + 1;
      |           ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer

