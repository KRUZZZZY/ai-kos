gnatmake wrong_increment.adb
 succeeds
gnatprove -P main.gpr --mode=flow
 succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
 fails as discussed in the lecture

wrong_increment.ads:6:19: medium: postcondition might fail, cannot prove X = X'Old + 1
    6 |       Post    => X = X'Old + 1 and X >= 1;
      |                  ^~~~~~~~~~~~~
gnatprove -P main.gpr --proof=progressive
reports in addition a possible overflow error
