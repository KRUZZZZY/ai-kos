gnatmake example.adb
gnatmake example2.adb
  both succeed
gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
  succeeds (no range check)
gnatprove -P main.gpr --mode=prove 
  fails because of possible overflow problems in  the lines
      A := A + 1;


example.adb:21:14: medium: overflow check might fail
   21 |      A := A + 1;
      |           ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: loop at line 10 should mention A in a loop invariant
   10 |   Outer: loop
      |          ^ here

example2.adb:25:14: medium: overflow check might fail
   25 |      A := A + 1;
      |           ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: loop at line 10 should mention A in a loop invariant
   10 |   Outer: loop
      |          ^ here





Note
~~~~
In a previous version
  spark ada rejected example2.adb
  because the condition
     if A = 6 then  
  is always false





 
