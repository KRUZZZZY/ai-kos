Program passes SPARK ada checks

gnatmake test.adb
  succeeds
gnatprove -P main.gpr --proof=progressive
  succeeds 
