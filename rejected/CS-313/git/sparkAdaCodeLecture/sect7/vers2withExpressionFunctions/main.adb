pragma SPARK_Mode;
with AS_Io_Wrapper; use AS_Io_Wrapper;
-- with Spark.Text_Io; use Spark.Text_Io;
with Simple_Railway; use Simple_Railway;


procedure Main
is
   subtype Mode is Simple_Railway.Mode;
   subtype Segment_State_Type is Simple_Railway.Segment_State_Type;
   subtype Signal_State_Type is Simple_Railway.Signal_State_Type;
   Success: Boolean;
   Route: Route_Type;
   The_Mode: Mode;
   
   Segment_State : Segment_State_Type;
   Signal_State  : Signal_State_Type;
   
begin
   As_Init_Standard_Input;
   As_Init_Standard_Output;
   Init(Segment_State,Signal_State);
   loop
      pragma Loop_Invariant(Signals_Correct (Segment_State,Signal_State  ));
      As_Put_Line(" ");
      Print_State(Segment_State,Signal_State);
      As_Put_Line(" ");
      Get_Action(Route, The_Mode);
      if The_Mode = Mode_Open
      then
         Open(Segment_State, Signal_State,Route, Success);
      else
         Move(Segment_State, Signal_State, Route, Success);
      end if;
      if Success
      then
         As_Put_Line("*** Success *** ");
      else
         As_Put_Line("*** Route not Allowed *** ");
         
      end if;
   end loop;
end Main;
