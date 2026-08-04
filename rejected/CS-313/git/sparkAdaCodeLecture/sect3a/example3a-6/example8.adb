with Ada.Text_Io;
use Ada.Text_Io;


Procedure Example8 is
   Answer : Character;
begin
   loop 
      Put("Answer yes (y) or no (n):");
      Get(Answer);
      if Answer = 'y' then
         Put_Line("You said yes");
         exit;
      elsif Answer = 'n' then
         Put_Line("You said no");
         exit;
      else
         Put_Line("You must type in y or n");
      end if;
   end loop;
   -- when as I misunderstood results in compiler error
   -- 
   -- Put_Line("You said Yes") when Answer = 'Y';
end Example8;
  
     

