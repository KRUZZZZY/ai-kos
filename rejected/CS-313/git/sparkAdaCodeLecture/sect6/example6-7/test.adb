Pragma SPARK_Mode;

package body Test is
   
   
   function Myfunction(A : Integer) return Integer is
   begin
      return A + 3;
   end Myfunction;

end Test;
