package body Example  
with SPARK_MODE
is
   
   
   function A1 (X : in Integer) return Integer
   is
   begin
      -- checking
      --    gnatprove -P main.gpr --proof=per_path
      -- reports an overflow check might fail
      -- checking
      --    gnatprove -P mainWithoutRangeCheck.gpr --proof=per_path
      -- reports no error
      return X + Glob;
   end A1;
   
   
   procedure Init 
   is
   begin
      Glob := 3;
   end Init;
     
end Example;

