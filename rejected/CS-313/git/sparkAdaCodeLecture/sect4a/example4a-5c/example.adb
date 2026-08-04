package body Example  
with SPARK_MODE is
     
   procedure Wrong_Exchange (X, Y  : in out Float)
   is
      T : Float;
   begin
      -- Errors will be reported as expected
      -- See README.txt for details
      T := X; X:= Y; Y := X;
   end Wrong_Exchange;
   
   
     
end Example;

