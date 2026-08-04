Pragma SPARK_Mode;

package Test is
   
   A : Integer;
     
     
   procedure Init
     with 
       Global => (Output => A),
       Depends => (A => null),
       Post => (A = 0);
   
   procedure Procedure1
     with 
       Global => (In_Out => A),
       Depends => (A => A),
       Post => (A = A'Old + 2);
   
   Procedure Main
     with 
       Global => (Output => A),
       Depends => (A => null),
       Post => (A = 2);
   
   
end Test;

