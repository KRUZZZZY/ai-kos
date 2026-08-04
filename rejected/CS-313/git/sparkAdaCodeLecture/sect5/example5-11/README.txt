gnatmake ex_assert_and_cut.adb
  succeeds
gnatprove -P main.gpr --proof=progressive 
  succeeds
