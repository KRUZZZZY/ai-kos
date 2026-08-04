gnatmake correct_increment.adb
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  succeeds
gnatprove -P main.gpr --proof=progressive
  reports a possible overflow problem as discussed in the lecture

correct_increment.adb:5:11: medium: overflow check might fail
    5 |   X := X + 1;
      |        ~~^~~

