Pragma SPARK_Mode;

package Example is
   
   procedure Example1(N,M : in out Integer)
     with 
       Depends => (N => (N,M),
                   M => M),
       Pre => (((M >=0 xor N < 0) or (if not (N > 0) then M > 0))
               or (for all X in 0 .. 3 => X = X)
               or (for Some X in Integer => X  = X)),
       Post => M = M'Old + 1;

end Example;



