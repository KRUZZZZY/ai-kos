package body Example  
with SPARK_MODE is
   
   procedure Exchange (X, Y  : in out Float) 
   is
      Tmp : Float;
   begin
      Tmp := X;
      X := Y;
      Y := Tmp;
   end Exchange;
   
   
   function A1 (X : in Float) return Float
   is
   begin
      return X + Glob;
   end A1;
   
   
   procedure Init is
   begin
      Glob := 3.0;
   end Init;
     
end Example;

