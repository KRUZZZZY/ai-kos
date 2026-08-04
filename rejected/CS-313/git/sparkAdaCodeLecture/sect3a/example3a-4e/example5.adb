with Ada.Text_Io, Ada.Integer_Text_IO;
use Ada.Text_Io, Ada.Integer_Text_Io ;


Procedure Example5 is
   subtype Year is Integer range 0 .. 2100;
   Integervar   : Integer := 2010;
   Yearvar  : Year;
  begin
     Put("Year = ");
     Get(Integervar);
     -- Put(Myyear);
     -- Myyear := Myyear + 1;
     -- Put(Myyear);
     if Integervar >= 0 and Integervar <= 2100 then
	   Yearvar := Integervar;
     else
	   Yearvar := 2100;
     end if;
     Integervar  := Yearvar;
     if Integervar < 2000
     then
	Put_Line("year < 2000");
     else
	Put_Line("year >= 2000");
     end if;
     
     
  end Example5;
  
     
	    
