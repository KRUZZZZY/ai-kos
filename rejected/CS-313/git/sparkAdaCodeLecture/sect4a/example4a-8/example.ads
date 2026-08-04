package Example 
with SPARK_MODE,  Abstract_State => AbsGlob
is
   
   function A1 (X : in Integer) return Integer
     with Global => AbsGlob;
   
   procedure  Init 
     with Global => (Output => AbsGlob);
   
   
end Example;
  
  

