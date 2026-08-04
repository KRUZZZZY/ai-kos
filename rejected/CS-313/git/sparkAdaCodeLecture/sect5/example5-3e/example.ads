Pragma SPARK_Mode;

package Example is
   
   type Mytype is new Integer range 0 .. 5;

   procedure Example1(N : in Integer; M : out Integer)
     with
       Depends => (M => N),
       Pre => (N in 0 .. 10),
       Post => (for all X in Integer => X = X and M = N + 1);

end Example;
   


