pragma SPARK_Mode;
package Test is 
   pragma Elaborate_Body(Test);
   
   Procedure Main(A : out Integer)
     with 
       Depends => (A => null),
       Post => (A = 2);
   
end Test;
