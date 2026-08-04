package Example 
with SPARK_MODE
is
   
   Glob : Float;
   
   procedure Exchange (X, Y  : in out Float); 
   
   function A1 (X : in Float) return Float
     with Global => Glob;

   
   procedure Init;
   
end Example;
  
  

