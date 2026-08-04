gnatmake main.adb
  succeeds without errors
gnatprove -P main.gpr --proof=per_path
  reports no errors.

