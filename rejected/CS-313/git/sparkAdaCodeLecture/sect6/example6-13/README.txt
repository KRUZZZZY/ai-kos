Program passes SparkAda checks

gnatmake example.adb
 succeeds
gnatprove -P main.gpr --proof=progressive
 succeeds
