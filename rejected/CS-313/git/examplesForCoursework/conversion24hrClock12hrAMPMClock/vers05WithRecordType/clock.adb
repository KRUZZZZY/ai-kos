pragma SPARK_Mode;


package body Clock is
   
   procedure To12Proc (H : in Hour; O : out Hours_Ampm) is
   begin
      if H >= 12 then O := Hours_Ampm'(Hours => H - 12,
                                       Mode  => Pm);
      else O := Hours_Ampm'(Hours => H,
                            Mode  => Am);
      end if;     
   end To12Proc;

     
end Clock;
     

   
     
   
