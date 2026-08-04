package body Example  
with SPARK_MODE
-- ,
--       Refined_State => (AbsGlob => Glob)  
is
   
   
   function A1 (X : in Integer) return Integer
   --      with Refined_Global => Glob 
   is
   begin
      -- gnatprove -P main.gpr --mode=prove
      --    causes error because of range check might fail
      -- gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
      --   succeeds
      return X + Glob;
   end A1;
   
   
   procedure Init 
   --     with Refined_Global => (Output => Glob)     
   is
   begin
      Glob := 3;
   end Init;
     
end Example;

