package body Example  
with SPARK_MODE is
     
   procedure Wrong_Exchange (X, Y  : in out Float)
   is
   begin
      X:= Y; 
      Y := X;
   end Wrong_Exchange;
   
   
     
end Example;

