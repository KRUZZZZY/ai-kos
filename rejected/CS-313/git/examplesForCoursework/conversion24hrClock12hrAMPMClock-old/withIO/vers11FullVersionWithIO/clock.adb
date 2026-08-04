pragma SPARK_Mode;


package body Clock is
   
   function To12 (T : Hour) return Hour12 is
   begin
      if T >= 12 then return Hour12(T - 12);
      else return Hour12(T);
      end if;
   end To12;
   
   
  procedure To12Proc (T : in Hour; U : out Hour12) is
  begin
     if T >= 12 then U := Hour12(T - 12);
     else U := Hour12(T);
     end if;
   end To12Proc;

     
end Clock;
     
     
   
     
   
