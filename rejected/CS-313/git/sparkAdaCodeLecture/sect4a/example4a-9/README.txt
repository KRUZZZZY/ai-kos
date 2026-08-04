gnatmake main.adb
  reports no errors
gnatprove -P main.gpr --proof=per_path
   reports

example.adb:15:16: medium: overflow check might fail
   15 |      return X + Glob;
      |             ~~^~~~~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at example.ads:8 should mention X and Glob in a precondition
    8 |   function A1 (X : in Integer) return Integer
      |   ^ here


gnatprove -P mainWithoutRangeCheck.gpr  --proof=per_path
   reports no error
