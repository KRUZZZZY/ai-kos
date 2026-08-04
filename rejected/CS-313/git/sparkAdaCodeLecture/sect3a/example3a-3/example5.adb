with Ada.Text_Io, Ada.Integer_Text_IO;
use Ada.Text_Io, Ada.Integer_Text_Io ;


Procedure Example5 is
   subtype Year is Integer range 0 .. 2100;
   type Day is (Mon,Tue,Wed,Thu,Fri,Sat,Sun);
   subtype Weekday is Day range Mon .. Fri;
   Myyear : Year := 2010;
   MydayInput : String(1 .. 3);
   Myday  : Weekday := Fri;
begin
   Put("Year = ");
   Get(Myyear);
   loop
      Put("Week Day as 3 letters = ");
      Get(MydayInput);
      if MydayInput = "Mon"
      then Myday := Mon; exit;
      elsif MydayInput = "Tue"
      then Myday := Tue; exit;       
      elsif MydayInput = "Wed"
      then Myday := Wed; exit;           
      elsif MydayInput = "Thu"
      then Myday := Thu; exit;                 
      elsif MydayInput = "Fri"
      then Myday := Fri; exit;                      
      else Put_Line("Weekday should have been one of Mon, Tue, Wed, Thu, Fri");
      end if;
   end loop;
   if Myday = Fri then
      Put_Line("Friday");
   else
      Put_Line("Not Friday");
   end if;
   if Myyear < 2000 then
      Put_Line("My year < 2000");
   else
      Put_Line("My year >= 2000");
   end if;
     
end Example5;
  
     

