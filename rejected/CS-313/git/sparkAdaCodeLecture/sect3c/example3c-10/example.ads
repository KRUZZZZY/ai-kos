package Example 
with SPARK_MODE 
is
   type Test is record
      A : Integer;
      B : Integer := 5;
   end record;
   
   -- doesn't compile and SPARK Ada gives error
   -- because no value given for component "B"
   -- Shows that default values in record are not allowed in SPARK Ada.
   -- A normal ada compiler should succeed but the one provided by gnat
   --   rejects this line
   X : Test := (A => 3);

   function f return Integer;
   
end Example;
  
  

