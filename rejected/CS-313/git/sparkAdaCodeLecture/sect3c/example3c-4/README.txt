The line
      A := A + 1;
fails if checked with
    gnatprove -P main.gpr --mode=prove
because of possible out of range error
using
   gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
it succeeds (no range check)

