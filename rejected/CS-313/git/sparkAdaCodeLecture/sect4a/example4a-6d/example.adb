package body Example  
with SPARK_MODE is
     
   procedure Strange_Exchange (X : out Float; Y  : in out Float) 
   is
   begin
      X:= Y; 
      Y := X;
   end Strange_Exchange;
   
   
     
end Example;

