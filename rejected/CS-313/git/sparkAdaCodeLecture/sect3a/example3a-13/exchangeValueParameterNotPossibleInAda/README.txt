testparameterpassing.adb 
   shows exchanging of parameters in a record type is allowed in ada
testparameterpassing2.adb 
   shows exchanging of in out parameters is possible
testparameterpassing3.adb 
   compilation fails 
   because in parameters fields of a record type cannot be changed.
testparameterpassing3.adb 
   compilation fails 
   because in parameters fields of a record type cannot be changed.

gnatprove -P main.gpr --proof=progressive
reports the problems regarding testparameterpassing3.adb


