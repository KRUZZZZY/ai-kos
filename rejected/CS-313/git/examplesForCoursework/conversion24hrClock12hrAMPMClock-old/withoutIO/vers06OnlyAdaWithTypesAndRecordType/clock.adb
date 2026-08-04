pragma SPARK_Mode;


package body Clock is
   
   function To12 (H : Hour) return Hours_Ampm is
   begin
      if H >= 12 then return Hours_Ampm'(Hours => Hour12(H - 12),
					Mode  => Pm);
      else return Hours_Ampm'(Hour12(H),
			     Mode => Am);
      end if;
   end To12;
   
   
  procedure To12Proc (H : in Hour; O : out Hours_Ampm) is
  begin
      if H >= 12 then O := Hours_Ampm'(Hours => Hour12(H - 12),
				      Mode  => Pm);
      else O := Hours_Ampm'(Hours => Hour12(H),
				  Mode  => Am);
      end if;     
   end To12Proc;

     
end Clock;
     
     
   
     
   
