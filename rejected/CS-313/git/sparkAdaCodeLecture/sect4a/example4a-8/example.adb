package body Example  
with SPARK_MODE,
  Refined_State => (AbsGlob => Glob)  
is
   Glob : Integer;
   
   function A1 (X : in Integer) return Integer
     with Refined_Global => Glob 
   is
   begin
      -- checking
      --     gnatprove -P main.gpr --proof=per_path
      -- reports overflow check might fail
      -- checking
      --    gnatprove -P mainWithoutRangeCheck.gpr  --proof=per_path
      -- reports no error   
      return X + Glob;
   end A1;
   
   
   procedure Init 
     with Refined_Global => (Output => Glob)     
   is
   begin
      Glob := 3;
   end Init;
     
end Example;

