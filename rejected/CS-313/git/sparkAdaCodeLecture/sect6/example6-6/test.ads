pragma SPARK_Mode;

package Test is
     
   
   procedure Init(A : out Integer)
     with 
       Depends => (A => null),
       Post => (A = 0);
   
   procedure Inc(A : in out Integer)
     with 
       Depends => (A => A),
       Pre  => (A >= 0),
       Post => (A >= 2);
   
   Procedure Main(A : out Integer)
     with 
       Depends => (A => null),
       Post => (A > 1);
   
   
end Test;

