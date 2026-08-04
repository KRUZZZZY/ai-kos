gnatmake example.adb
  suceeds without errors

gnatprove -P main.gpr --proof=per_path
reports overflow check problems:

example.adb:25:14: medium: overflow check might fail
   25 |      X := Y + Z;
      |           ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at example.ads:16 should mention Y and Z in a precondition
   16 |   procedure Test4(X : out Integer; Y,Z : in Integer)
      |   ^ here

example.adb:31:14: medium: overflow check might fail
   31 |      X := X + 1;
      |           ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at example.ads:19 should mention X in a precondition
   19 |   procedure Test5(X : in out Integer)
      |   ^ here

example.adb:37:14: medium: overflow check might fail
   37 |      X := X + Y;
      |           ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at example.ads:23 should mention X and Y in a precondition
   23 |   procedure Test6(X : in out Integer; Y : in Integer)
      |   ^ here

gnatprove -P mainWithoutRangeCheck.gpr  --proof=per_path
reports no errors
