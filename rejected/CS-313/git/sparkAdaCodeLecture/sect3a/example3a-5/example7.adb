with Ada.Text_Io;
use Ada.Text_Io;


Procedure Example7 is
   Answer : Character;
begin
   Put("Say y or n :");
   Get(Answer);
   if Answer = 'y' then
      Put_Line("You said yes");
   elsif Answer = 'n' then
      Put_Line("You said no");
   else
      Put_Line("You must type in y or n");
   end if;
   -- when as I misunderstood results in compiler error
   -- 
   -- Put_Line("You said Yes") when Answer = 'Y';
end Example7;
  

	    
