package Example 
with SPARK_MODE
is
   Glob : Integer;
   
   procedure A1 (X : in Integer)
     with Global => (In_out => Glob);
   
   procedure A2 (X : out Integer)
     with Global => (Input =>  Glob);   
   
   procedure A3 (X : in Integer)
     with Global => (Output =>  Glob);   
   
end Example;
  
  

