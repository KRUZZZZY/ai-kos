This code compiles

gnatprove -P main.gpr --mode=prove
errors
  - array index out of range
  - range check might fail (if using main.gpr)
gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
reports
  - array index out of range

gnatprove -P mainWithoutRangeCheck.gpr --mode=flow
reports no error
