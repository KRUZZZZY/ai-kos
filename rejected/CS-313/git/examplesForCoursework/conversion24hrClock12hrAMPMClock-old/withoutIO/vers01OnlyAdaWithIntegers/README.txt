gnatmake clock.adb
  succeeds
gnatprove -P main.gpr --proof=progressive
  succeeds
