package body Example  
with SPARK_MODE is
   
   
   procedure A1 (X : in Integer; Y : out Integer)
   is
   begin
      if X > 0 then
         Y := 1;
      end if;
   end A1;
      
      
end Example;

