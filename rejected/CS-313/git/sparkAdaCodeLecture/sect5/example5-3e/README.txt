Trying out syntax for formulas in pre and post conditions.
Formulas don't make sense, are just used to demonstrate formulas.

gnatmake example.adb
  succeeds

gnatprove -P main.gpr  --proof=progressive
succeeds
