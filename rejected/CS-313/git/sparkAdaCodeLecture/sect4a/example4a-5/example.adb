package body Example  
with SPARK_MODE is
     
   procedure Exchange (X, Y  : in out Float)
   is
      T : Float;
   begin
      -- There are several errors as expected from the lecture
      -- see README.txtx
      T := X; X:= Y; Y := X;
   end Exchange;
   
   
     
end Example;

