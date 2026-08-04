gnatmake exchange_and_count.adb
  succeeds without errors
gnatprove -P main.gpr --proof=per_path
  succeeds without errors

