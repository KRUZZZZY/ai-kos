This passes the spark ada checks

gnatmake example.adb
  succeeds with no errors

gnatprove -P main.gpr --proof=per_path
  succeeds with no errors
