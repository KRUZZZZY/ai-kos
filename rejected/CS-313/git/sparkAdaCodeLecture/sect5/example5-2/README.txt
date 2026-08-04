Trying out syntax for formulas in pre and post conditions.
Formulas don't make sense, are just used to demonstrate formulas.
The code was not meant to pass the verification conditions

gnatmake example.adb
  succeeds

gnatprove -P mainWithoutRangeCheck.gpr  --proof=progressive
gives error 
example.ads:13:11: medium: postcondition might fail
   13 |  Post => M = M'Old + 1;
      |          ^~~~~~~~~~~~~



gnatprove -P main.gpr --proof=progressive
causes errors, it was not intended to get this example correct
example5-3 is a variant in which these errors have been repaired.

data and information flow analysis succeeds:
gnatprove -P main.gpr --mode=flow


This example demonstrates that the usage of connectives

if .. then ..
xor
or

worked.

for all, for some was syntactically accepted as a condition but
didn't result in generation of verification condition in why3

