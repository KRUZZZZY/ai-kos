with Ada.Text_Io;
use Ada.Text_Io;


Procedure Example4 is
   type Gender is (Male, Female);
   Mygender : Gender;
begin
   Mygender := Male;
   if Mygender = Male then
      Put_Line("Male");
   else
      Put_Line("Female");
   end if;
   Mygender := Female;
   if Mygender = Male then
      Put_Line("Male");
   else
      Put_Line("Female");
   end if;
end Example4;
  
     

