Program succeeds including overflow checks

gnatmake test.adb
 succeeds
gnatprove -P main.gpr --proof=progressive
 succeeds
