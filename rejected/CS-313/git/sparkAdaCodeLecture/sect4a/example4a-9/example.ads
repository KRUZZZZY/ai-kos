package Example 
with SPARK_MODE
is
   
   Glob : Integer;
   
   
   function A1 (X : in Integer) return Integer
     with Global => Glob;
   
   procedure  Init 
     with Global => (Output => Glob);
   
   
end Example;
  
  

