pragma SPARK_Mode;

with AS_IO_Wrapper;  use AS_IO_Wrapper; 
with Loopexample; use  Loopexample;

procedure Main is
   N, Res : Integer;
   User_Input : String(1 .. 20);
   Last : Integer;
begin
   -- First we initialise standard_input and standard output
   AS_Init_Standard_Output;
   AS_Init_Standard_Input;   
   loop   
      -- Print on screen "Type in some number"
      AS_Put("Type in a number: ");
      loop
         -- ask for an  integer (in variable X) until an integer has been entered
         --   if something else has been entered ask again
         AS_Get(N,"Please type in an integer; please try again");
         exit when N in 1 .. 1000;
         AS_Put_Line("Please enter a number in 1 .. 1000");
      end loop;      
      LoopProc(N,Res);
      AS_Put("Res = ");
      AS_Put_Line(Res);   
      loop
         As_Put("Do you want to try again (y/n)? ");
         As_Get_Line(User_Input, Last);
         exit when Last > 0;
         As_Put_Line("Please enter a non-empty string");
      end loop;
      exit when User_Input(1 .. 1) = "n";
   end loop;           
end Main;
