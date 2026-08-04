package body Example  
with SPARK_MODE is
     
   procedure Test (X : in Float; Y : out Float; Z : out Float) 
   is
   begin
      Y := X; 
      Z := Y;
   end Test;
   
   
     
end Example;

