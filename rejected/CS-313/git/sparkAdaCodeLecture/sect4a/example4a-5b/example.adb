package body Example  
with SPARK_MODE is
     
   procedure Exchange (X, Y  : in out Float)
   is
      T : Float;
   begin
      T := X; X:= Y; Y := T;
   end Exchange;
   
   
     
end Example;

