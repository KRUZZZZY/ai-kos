pragma SPARK_Mode;

package Test is
     
   
   function Myfunction(A : Integer) return Integer
     with Post => (Myfunction'Result = A + 3);
   
   
   
end Test;

