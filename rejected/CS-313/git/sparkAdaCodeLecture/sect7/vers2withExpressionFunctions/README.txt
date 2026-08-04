gnatmake main.adb
  succeeds
gnatprove -P main.gpr --proof=progressive
  succeeds
