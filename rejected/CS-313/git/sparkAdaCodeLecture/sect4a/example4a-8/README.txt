gnatmake example.adb
  succeeds with no errors
gnatprove -P main.gpr --proof=per_path
   reports
example.adb:17:16: medium: overflow check might fail
   17 |      return X + Glob;
      |             ~~^~~~~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at example.ads:5 should mention X and Glob in a precondition
    5 |   function A1 (X : in Integer) return Integer
      |   ^ here


checking
    gnatprove -P mainWithoutRangeCheck.gpr  --proof=per_path
 reports no error   
