gnatmake example.adb
  succeeds with no errors
gnatprove -P main.gpr --proof=per_path
  reports no errors
