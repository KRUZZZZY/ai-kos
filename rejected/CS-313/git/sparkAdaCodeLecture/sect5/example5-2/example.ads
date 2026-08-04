Pragma SPARK_Mode;

procedure Example(N,M : in out Integer)
  with Depends => (N => (N,M),
                   M => M),
  Pre => (((M >=0 xor N < 0) or (if (not (N > 0)) then M > 0))),
--           or (for all X in 0 .. 5 => X = X)),
--  or (for Some X in Integer => X  = X)),
  
-- Postcondition might fail 
-- this is an example to only demonstrate the syntax of verification conditions
-- there was no aim at having the post conditions fulfilled.
  Post => M = M'Old + 1;
  
   


