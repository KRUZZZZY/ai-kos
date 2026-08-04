gnatmake simple2.adb
 succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
 succeeds
gnatprove -P main.gpr --proof=progressive
 succeeds
