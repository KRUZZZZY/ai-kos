Pragma SPARK_Mode;

package Example is
   
   type Mytype is new Integer range 0 .. 5;

   procedure Example1(N : in Integer; M : in out Integer)
     with
       Depends => (M => (M,N)),
       Pre => (N >= 5),
       Post => (for all X in Integer => X = X and M = M'Old + 1);

end Example;
   


