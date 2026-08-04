Pragma SPARK_Mode;

package body Test is
   
   procedure Testproc(X : in Integer; Y : out Integer) is
   begin
      Y:= F(X);
   end Testproc;
   
   
end Test;

