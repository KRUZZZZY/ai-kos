pragma SPARK_Mode;
with Spark.Text_Io; use Spark.Text_Io;

package Simple_Railway is
   
   type One_Signal_State is (Red,Green);
   
   type Mode is (Mode_Open, Mode_Move);
   
   type Route_Type is (Route_Left_Middle,
                       Route_Middle_Left,
                       Route_Middle_Right,
                       Route_Right_Middle,
                       Route_Leave_Left,
                       Route_Enter_Left,
                       Route_Leave_Right,
                       Route_Enter_Right);
   
   type One_Segment_State is (Occupied_Standing,
                              Occupied_Moving_Left,
                              Occupied_Moving_Right,
                              Reserved_Moving_From_Left,
                              Reserved_Moving_From_Right,
                              Free);
   -- type BlockedType is (Blocked, Unblocked);
   
   type Segment_State_Type is
      record
         Left,
         Middle,
         Right: One_Segment_State;
      end record;
   
   type Signal_State_Type is
      record
         Leave_Left,
         Enter_Left,
         Left_Middle,
         Middle_Left,
         Middle_Right,
         Right_Middle,
         Leave_Right,
         Enter_Right: One_Signal_State;
      end record;
   
   
   function Signals_Correct (Segment_State : Segment_State_Type;
                             Signal_State  : Signal_State_Type) 
                             return Boolean is
     ((if Signal_State.Middle_Left = Green
      then (Segment_State.Left = Reserved_Moving_From_Right
        and Segment_State.Middle = Occupied_Moving_Left))
      and
        (if Signal_State.Middle_Right = Green
         then (Segment_State.Right = Reserved_Moving_From_Left
           and Segment_State.Middle = Occupied_Moving_Right))
      and
        (if Signal_State.Left_Middle = Green
         then (Segment_State.Middle = Reserved_Moving_From_Left
           and Segment_State.Left = Occupied_Moving_Right))
      and
        (if Signal_State.Right_Middle = Green
         then (Segment_State.Middle = Reserved_Moving_From_Right
           and Segment_State.Right = Occupied_Moving_Left))
	
      and
        (if Signal_State.Leave_Left = Green
         then Segment_State.Left = Occupied_Moving_Left)
	
      and
        (if Signal_State.Enter_Left = Green
         then Segment_State.Left = Reserved_Moving_From_Left)
	
      and
        (if Signal_State.Leave_Right = Green
         then Segment_State.Right = Occupied_Moving_Right)
	
      and
        (if Signal_State.Enter_Right = Green
         then Segment_State.Right = Reserved_Moving_From_Right));
      
   function Segment_Occupied(Segment_State : One_Segment_State) return Boolean is
     (Segment_State = Occupied_Moving_Left or
        Segment_State = Occupied_Moving_Right or
          Segment_State= Occupied_Standing);
      
      
   function Trains_Stay (Segment_State_Old, 
                         Segment_State_New : Segment_State_Type)
                            return Boolean is
     ((if Segment_Occupied(Segment_State_Old.Left)
      then  Segment_Occupied(Segment_State_New.Left)) and
        (if Segment_Occupied(Segment_State_Old.Middle)
         then  Segment_Occupied(Segment_State_New.Middle)) and	   
          (if Segment_Occupied(Segment_State_Old.Right)
           then  Segment_Occupied(Segment_State_New.Right)));
	 
	 
   function Move_Trains_Correct (Segment_State_Old, 
                                 Segment_State_New : Segment_State_Type;
                                 Route: Route_Type)
                                return Boolean is	   
     ((if Segment_State_Old.Left = Occupied_Moving_Right
      then
        (Segment_State_New.Left = Occupied_Moving_Right
         or
           (Route = Route_Left_Middle
            and Segment_State_Old.Middle = Reserved_Moving_From_Left
            and Segment_State_New.Left = Free
            and Segment_State_New.Middle = Occupied_Standing)))
      and
        (if Segment_State_Old.Left = Occupied_Standing
         then
            Segment_State_New.Left = Occupied_Standing)
      and
        (if Segment_State_Old.Left = Occupied_Moving_Left
         then
           (Segment_State_New.Left = Occupied_Moving_Left
            or
              (Route = Route_Leave_Left
               and Segment_State_New.Left = Free)))
      and
        (if Segment_State_Old.Middle = Occupied_Moving_Right
         then
           (Segment_State_New.Middle = Occupied_Moving_Right
            or
              (Segment_State_Old.Right = Reserved_Moving_From_Left
               and
                 Segment_State_New.Middle = Free and
                   Segment_State_New.Right = Occupied_Standing)))
      and
        (if Segment_State_Old.Middle = Occupied_Moving_Left
         then
           (Segment_State_New.Middle = Occupied_Moving_Left
            or
              (Segment_State_Old.Left = Reserved_Moving_From_Right
               and
                 Segment_State_New.Middle = Free and
                   Segment_State_New.Left = Occupied_Standing)))
      and
        (if Segment_State_Old.Middle = Occupied_Standing
         then
            Segment_State_New.Middle = Occupied_Standing)
      and
        (if Segment_State_Old.Right = Occupied_Moving_Left
         then
           (Segment_State_New.Right = Occupied_Moving_Left
            or
              (Segment_State_Old.Middle = Reserved_Moving_From_Right
               and Segment_State_New.Right = Free
               and Segment_State_New.Middle = Occupied_Standing)))
      and
        (if Segment_State_Old.Left = Occupied_Standing
         then
            Segment_State_New.Left = Occupied_Standing));
	    
	    
	    
   procedure Init(Segment_State : out Segment_State_Type;
                  Signal_State  : out Signal_State_Type)   With
     Depends => (Signal_State => null,
                 Segment_State => null),
     Post => (Signals_Correct(Segment_State,Signal_State));
	    
	    
	    
	    
   procedure Open(Segment_State : in out Segment_State_Type;
                  Signal_State  : in out Signal_State_Type;
                  Route         : in Route_Type;
                  Success       : out Boolean)
     with 
       Depends => (Segment_State => (Segment_State,Route),
                   Success       => (Segment_State,Route),
                   Signal_State  => (Segment_State,Route,Signal_State)),
       Pre => (Signals_Correct(Segment_State,Signal_State)),	
       Post=> (Signals_Correct(Segment_State,Signal_State) and
                 Trains_Stay(Segment_State'Old,Segment_State));
	    
	    
	    
	    
	    
   procedure Move(Segment_State : in out Segment_State_Type;
                  Signal_State  : in out Signal_State_Type;
                  Route         : in Route_Type;
                  Success       : out Boolean) with
     Depends => (Signal_State  =>  (Segment_State, Route, Signal_State),
                 Segment_State =>  (Segment_State, Route, Signal_State),
                 Success       =>  (Segment_State, Route, Signal_State)),
     Pre => (Signals_Correct(Segment_State,Signal_State)),	
     Post=> (Signals_Correct(Segment_State,Signal_State) and
               Move_Trains_Correct(Segment_State'Old,Segment_State,Route));     
	    
	    
	    
	    
	    
   procedure Print_One_Signal(The_Signal_State: in One_Signal_State) with
     Global => (In_Out => Standard_Output),
     Depends => (Standard_Output => (Standard_Output, The_Signal_State));
	    
	    
   procedure Print_One_Segment_State(the_State: in One_Segment_State) with
     Global => (In_Out => Standard_Output),
     Depends => (Standard_Output => (Standard_Output, The_State));
	    
	    
	    
   procedure Print_State(Segment_State : in Segment_State_Type;
                         Signal_State  : in Signal_State_Type) with
     Global => (In_Out => Standard_Output),
     Depends => (Standard_Output => (Standard_Output, Segment_State,Signal_State));
	    
	    
	    
	    
   procedure Get_Action(Route    : out Route_Type;
                        The_Mode : out Mode) with  
     Global => (In_Out => (Standard_Input,Standard_Output)),
     Depends => (Standard_Output => (Standard_Output, Standard_Input),
                 Standard_Input =>   Standard_Input,
                 Route =>   Standard_Input,
                 The_Mode =>   Standard_Input);
	    
end Simple_Railway;
