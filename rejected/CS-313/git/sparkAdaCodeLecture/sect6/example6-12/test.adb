Pragma SPARK_Mode;

package body Test is
   
   procedure Test1 (X,Y : in out Integer) is
   begin
      X := X + 1;
      Y := Y + 1;
   end Test1;
end Test;

