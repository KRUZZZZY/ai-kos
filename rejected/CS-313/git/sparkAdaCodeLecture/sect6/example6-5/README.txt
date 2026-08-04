This is an example which shows that 
we can in the replace file have the signatures of the adb file added automatically.
The depends clauses and verification conditions are added to the adb file.
Note that we need to add 
   Procedure Test1(A : out Integer)
to the ads file despite the pragma Elaborate_Body(Test);
  otherwise we get an error when running
    gnatprove -P main.gpr --proof=progressive
test.adb:20:14: warning: procedure "Test1" is not referenced [-gnatwu]
   20 |   Procedure Main(A : out Integer)
      |             ^~~~



gnatmake test.adb
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
  succeeds
gnatprove -P main.gpr --proof=progressive
  reports a possible overflow error

test.adb:16:13: medium: overflow check might fail
   16 |      A:= A + 2;
      |          ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at line 12 should mention A in a precondition
   12 |   procedure Inc(A : in out Integer)
      |   ^ here

