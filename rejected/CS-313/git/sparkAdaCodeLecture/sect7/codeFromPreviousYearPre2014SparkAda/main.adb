
with Simple_Railway, Spark_IO;
use type Simple_Railway.Mode;
procedure Main
  is
   Success: Boolean;
   Route: Simple_Railway.Route_Type;
   The_Mode: Simple_Railway.Mode;
   begin
      Simple_Railway.Init;
      loop
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           " ",
                           0);
         Simple_Railway.Print_State;
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           " ",
                           0);
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
            Spark_IO.Put_Line(Spark_IO.Standard_Output,
                              "*** Success *** ",
                              0);
         else
            Spark_IO.Put_Line(Spark_IO.Standard_Output,
                              "*** Route not Allowed *** ",
                              0);

         end if;
      end loop;
   end Main;
