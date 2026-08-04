pragma SPARK_Mode;
package Test is 
   procedure Init(A : out Integer)
     with 
       Depends => (A => null),
       Post => (A = 0);
   
   procedure Inc(A : in out Integer)
     with 
       Depends => (A => A),
       Post => (A = A'Old + 2);
   
   procedure Main(A : out Integer)
     with 
       Depends => (A => null),
       Post => (A = 2);
   

end Test;
