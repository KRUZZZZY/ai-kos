package body Example 
with SPARK_MODE => off
is
   procedure Exchange(X : in out Boolean;  Y : in out Boolean) is
   begin
      X := X xor Y;
      Y := X xor Y;      
      X := X xor Y;      
   end Exchange;   
   
end Example;

