gnatprove -P main.gpr --mode=prove
   fails because of a possible out of range error
gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
   succeeds (no range condition check)
gnatprove -P main.gpr --mode=flow
  succeeds (only flow analysis)

