package body Example 
with SPARK_MODE is
   
   Function F(X : Integer )  return Integer
   is
      
   begin
      -- gnatprove -P main.gpr --mode=prove
      --    fails because of overflow might fail
      -- gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
      --    succeeds
      
      return G(X + 1);
   end F;
   
   
   Function G(X : Integer )  return Integer
   is
      
   begin
      -- gnatprove -P main.gpr --mode=prove
      --    fails because of overflow might fail
      -- gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
      --    succeeds

      return F(X + 1);
   end G;
   
   
   
end Example;
