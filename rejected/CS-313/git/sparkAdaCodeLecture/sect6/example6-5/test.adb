pragma SPARK_Mode;
package body Test is

   procedure Init(A : out Integer)
     with 
       Depends => (A => null),
       Post => (A = 0) is
   begin
      A := 0;
   end Init;

   
   procedure Inc(A : in out Integer)
     with 
       Depends => (A => A),
       Post => (A = A'Old + 2) is
   begin
      A:= A + 2;
   end Inc;
      
   
   Procedure Main(A : out Integer) is
   begin
      Init(A);
      Inc(A);
   end Main;
      
end Test;

