pragma SPARK_Mode;


package body Clock is
   
  procedure To12Proc (T : in Integer; U : out Integer) is
  begin
     if T >= 12 then U := T - 12;
     else U := T;
     end if;
   end To12Proc;

     
end Clock;
     
     
   
     
   
