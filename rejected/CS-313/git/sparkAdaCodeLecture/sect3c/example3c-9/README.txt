gnatprove -P main.gpr --mode=prove
  gives errors because range check might fails.
gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
  succeeds
