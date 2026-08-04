Pragma SPARK_Mode;

package Example is
   
   type Mytype is new Integer range 0 .. 5;

   procedure Example1(N : in Integer; M : in out Integer)
     with 
       Depends => (M => (M,N)),
       Pre => ((if N >= 5 then N >= 3) 
               and (if N >= 5 then N >=3 else N < 5)
               and (if N >= 5 then N >=3 and N >= 3 else N < 5 and N < 3)
               and (if N >= 5 then (N >=3 and N >= 2) else (N < 5 and N < 3))),      
   --           or (for all X in Mytype => X = X)),
   --  or (for Some X in Integer => X  = X)),
     Post => (for all X in Integer => X = X and M = M'Old + 1);

end Example;
   


