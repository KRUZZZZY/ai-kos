with SPARK.Text_IO; use SPARK.Text_IO;
with Simple_Railway;
use type Simple_Railway.Mode;
procedure Main
is
   Success: Boolean;
   Route: Simple_Railway.Route_Type;
   The_Mode: Simple_Railway.Mode;
begin
   Simple_Railway.Init;
   loop
      Put_Line(" ");
      Simple_Railway.Print_State;
      Put_Line(" ");
      Simple_Railway.Get_Action(Route,
                                The_Mode);
      if The_Mode = Simple_Railway.Mode_Open
      then
         Simple_Railway.Open(Route,
                             Success);
      else
         Simple_Railway.Move(Route,
                             Success);
      end if;
      if Success
      then
         Put_Line("*** Success *** ");
      else
         Put_Line("*** Route not Allowed *** ");

      end if;
   end loop;
end Main;
