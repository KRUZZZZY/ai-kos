This example demonstrates that if you instead of an expression function you add an
   ordinary function, SPARK Ada doesn't use the body of the expression function, 
   and therefore is not able to prove the verification conditions
The proof of the post condition fails.

gnatmake test.adb
  succeeds

both
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
gnatprove -P main.gpr --proof=progressive

fail

test.ads:11:14: medium: postcondition might fail
   11 |     Post => Cond (X,Y);
      |             ^~~~~~~~~
  possible fix: you should consider adding a postcondition to function Cond or turning it into an expression function
