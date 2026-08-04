package body Example 
with SPARK_MODE is
   
   Function F(X : Integer )  return Integer
   is
      
   begin
      -- gnatprove -P main.gpr --mode=prove
      --    fails because of overflow might fail
      -- gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
      --    succeeds
      --
      -- Spark ada 2015 detected an infinite loop
      -- Spark Ada 2021 doesn't see this problem anymore.
      return F(X + 1); 
   end F;
   
end Example;
