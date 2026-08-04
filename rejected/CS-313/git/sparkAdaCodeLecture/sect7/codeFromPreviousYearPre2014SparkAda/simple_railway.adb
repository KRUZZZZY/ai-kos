package body Simple_Railway
is

   procedure Open(Route: in Route_Type;
                        Success: out Boolean) is
      begin
         Success := False;
         if Route  = Route_Left_Middle
         then
            if (Segment_State.Left = Occupied_Standing
                and
                Segment_State.Middle = Free)
            then
               Segment_State.Left:= Occupied_Moving_Right;
               Segment_State.Middle:= Reserved_Moving_From_Left;
               Signal_State.Left_Middle:= Green;
               Success := True;
            else
               Success := False;
            end if;
         elsif Route  = Route_Right_Middle
         then
            if (    Segment_State.Right = Occupied_Standing
                and Segment_State.Middle = Free)
            then
               Segment_State.Right:= Occupied_Moving_Left;
               Segment_State.Middle:= Reserved_Moving_From_Right;
               Signal_State.Right_Middle:= Green;
               Success := True;
            else
               Success := False;
            end if;
         elsif Route = Route_Middle_Left
           then
              if (Segment_State.Middle = Occupied_Standing
                  and Segment_State.Left = Free)
              then
                 Segment_State.Middle:= Occupied_Moving_Left;
                 Segment_State.Left := Reserved_Moving_From_Right;
                 Signal_State.Middle_Left:= Green;
               Success := True;
            else
               Success := False;
            end if;
         elsif Route = Route_Middle_Right
           then
              if (Segment_State.Middle = Occupied_Standing
                  and Segment_State.Right = Free)
              then
                 Segment_State.Middle := Occupied_Moving_Right;
                 Segment_State.Right := Reserved_Moving_From_Left;
                 Signal_State.Middle_Right:= Green;
               Success := True;
            else
               Success := False;
            end if;
         elsif Route = Route_Enter_Left
           then
              if Segment_State.Left = Free
              then
                 Segment_State.Left := Reserved_Moving_From_Left;
                 Signal_State.Enter_Left:= Green;
                 Success := True;
              else
                 Success := False;
            end if;
         elsif Route = Route_Enter_Right
           then
              if Segment_State.Right = Free
              then
                 Segment_State.Right := Reserved_Moving_From_Right;
                 Signal_State.Enter_Right:= Green;
                 Success := True;
            else
               Success := False;
            end if;
         elsif Route = Route_Leave_Left
         then
            if Segment_State.Left = Occupied_Standing
              then
                 Segment_State.Left := Occupied_Moving_Left;
                 Signal_State.Leave_Left:= Green;
                 Success := True;
              else
                 Success := False;
            end if;
         elsif Route = Route_Leave_Right
         then
            if Segment_State.Right = Occupied_Standing
            then
               Segment_State.Right := Occupied_Moving_Right;
               Signal_State.Leave_Right:= Green;
               Success := True;
              else
                 Success := False;
            end if;
         end if;
      end Open;


   procedure Move(Route: in Route_Type;
                        Success: out Boolean) is
      begin
         Success := False;
         if Route  = Route_Left_Middle
         then
            if (Segment_State.Left = Occupied_Moving_Right
                and
		  Segment_State.Middle = Reserved_Moving_From_Left
		  and
	          Signal_State.Left_Middle= Green)
            then
               Signal_State.Left_Middle:= Red;
               Segment_State.Left:= Free;
               Segment_State.Middle:= Occupied_Standing;
               Success := True;
            else
               Success := False;
            end if;
         elsif Route  = Route_Right_Middle
         then
            if (    Segment_State.Right = Occupied_Moving_Left
		      and Segment_State.Middle = Reserved_Moving_From_Right
		      and Signal_State.Right_Middle = Green)
            then
               Signal_State.Right_Middle:= Red;
               Segment_State.Right:= Free;
               Segment_State.Middle:= Occupied_Standing;
               Success := True;
            else
               Success := False;
            end if;
         elsif Route = Route_Middle_Left
           then
              if (Segment_State.Middle = Occupied_Moving_Left
		    and Segment_State.Left = Reserved_Moving_From_Right
		    and Signal_State.Middle_Left = Green)
              then
                 Signal_State.Middle_Left:= Red;
                 Segment_State.Middle:= Free;
                 Segment_State.Left := Occupied_Standing;
               Success := True;
            else
               Success := False;
            end if;
         elsif Route = Route_Middle_Right
           then
              if (Segment_State.Middle = Occupied_Moving_Right
		    and Segment_State.Right = Reserved_Moving_From_Left
		    and Signal_State.Middle_Right = Green)
              then
                 Signal_State.Middle_Right:= Red;
                 Segment_State.Middle := Free;
                 Segment_State.Right := Occupied_Standing;
               Success := True;
            else
               Success := False;
            end if;
         elsif Route = Route_Enter_Left
           then
              if (Segment_State.Left = Reserved_Moving_From_Left
		  and Signal_State.Enter_Left = Green)
              then
                 Signal_State.Enter_Left:= Red;
                 Segment_State.Left := Occupied_Standing;
                 Success := True;
              else
                 Success := False;
            end if;
         elsif Route = Route_Enter_Right
           then
              if (Segment_State.Right = Reserved_Moving_From_Right
		    and Signal_State.Enter_Right= Green)
              then
                 Signal_State.Enter_Right:= Red;
                 Segment_State.Right := Occupied_Standing;
                 Success := True;
            else
               Success := False;
            end if;
         elsif Route = Route_Leave_Left
         then
            if (Segment_State.Left = Occupied_Moving_Left
		   and Signal_State.Leave_Left = Green)
              then
                 Signal_State.Leave_Left:= Red;
                 Segment_State.Left := Free;
                 Success := True;
              else
                 Success := False;
            end if;
         elsif Route = Route_Leave_Right
         then
            if (Segment_State.Right = Occupied_Moving_Right
		  and Signal_State.Leave_Right = Green)
              then
                 Signal_State.Leave_Right:= Red;
                 Segment_State.Right := Free;
                 Success := True;
              else
                 Success := False;
            end if;
         end if;
      end Move;

procedure Print_One_Signal(The_Signal_State: in One_Signal_State) is
   begin
      case The_Signal_State is
        when Red => Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "Red",
                                        0);
        when Green =>Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "Green",
                                        0);
      end case;
   end Print_One_Signal;

procedure Print_One_Segment_State(the_State: in One_Segment_State) is
   begin
      case The_State is
        when Occupied_Standing => Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "Occupied_Standing",
                                        0);
        when Occupied_Moving_Left => Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "Occupied_Moving_Left",
                                        0);
        when Occupied_Moving_Right => Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "Occupied_Moving_Right",
                                        0);
        when Reserved_Moving_From_Left => Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "Reserved_Moving_From_Left",
                                        0);
        when Reserved_Moving_From_Right => Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "Reserved_Moving_From_Right",
                                        0);
        when Free => Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "Free",
                                        0);
      end case;
   end Print_One_Segment_State;


procedure Print_State is
   begin
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        "Starting From Left",
                                        0);
      Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "V",
                                        0);
      Print_One_Signal(Signal_State.Enter_Left);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        " ",
                                        0);

      Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "^",
                                        0);
      Print_One_Signal(Signal_State.Leave_Left);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        " ",
                                        0);
      Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "Segment_Left:",
                                        0);

      Print_One_Segment_State(Segment_State.Left);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        " ",
                                        0);
      Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "V",
                                        0);
      Print_One_Signal(Signal_State.Left_Middle);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        " ",
                                        0);

      Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "^",
                                        0);
      Print_One_Signal(Signal_State.Middle_Left);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        " ",
                                        0);
      Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "Segment_Middle:",
                                        0);
      Print_One_Segment_State(Segment_State.Middle);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        " ",
                                        0);
      Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "V",
                                        0);
      Print_One_Signal(Signal_State.Middle_Right);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        " ",
                                        0);
      Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "^",
                                        0);
      Print_One_Signal(Signal_State.Right_Middle);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        " ",
                                        0);
      Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "Segment_Right:",
                                        0);
      Print_One_Segment_State(Segment_State.Right);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        "  ",
                                        0);

      Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "V",
                                        0);
      Print_One_Signal(Signal_State.Leave_Right);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        " ",
                                        0);

      Spark_IO.Put_String(Spark_IO.Standard_Output,
                                        "^",
                                        0);
      Print_One_Signal(Signal_State.Enter_Right);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        " ",
                                        0);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        "Right",
                                        0);
      Spark_IO.Put_Line(Spark_IO.Standard_Output,
                                        "  ",
                                        0);

   end Print_State;


procedure Get_Action(Route: out Route_Type;
                    The_Mode: out Mode) is
   subtype Index_3 is Integer range 1 .. 3;
   subtype String_3 is String(Index_3);
   Item : String_3;
   subtype Index_1 is Integer range 1 .. 1;
   subtype String_1 is String(Index_1);
   Item_1 : String_1;
   subtype Index_2 is Integer range 1 .. 2;
   subtype String_2 is String(Index_2);
   Item_2 : String_2;
   subtype String_Slice_1 is Integer range 1 ..1;
   subtype String_Slice_2 is Integer range 2 ..3;
   Stop : Integer;
   Success_Route: Boolean;
   Success_Mode: Boolean;

   begin
      loop
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           "Select Mode and Route",
                           0);
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           "First Letter O for Open, M for Move",
                           0);
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           "Letters 2 and 3 as follows",
                           0);
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           "ML for Middle_Left",
                           0);
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           "LM for Left_Middle",
                           0);
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           "RM for Right_Middle",
                           0);
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           "MR for Middle_Right",
                           0);
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           "LL for Leave_Left",
                           0);
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           "EL for Enter_Left",
                           0);
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           "LR for Leave_Right",
                           0);
         Spark_IO.Put_Line(Spark_IO.Standard_Output,
                           "ER for Enter_Right",
                           0);
         loop
            Spark_IO.Get_String(Spark_IO.Standard_Input,
                                Item,
                                Stop);
            exit when not (Stop = 0);
         end loop;
         Success_Mode  := False;
         Item_1 := " ";
         Item_1(1):= Item(1);
         Item_2 := "  ";
         Item_2(1):= Item(2);
         Item_2(2):= Item(3);
         The_Mode := Mode_Open;
         if Item_1 = "O"
         then
            The_Mode := Mode_Open;
            Success_Mode:= True;
         elsif Item_1 = "M"
         then
            The_Mode := Mode_Move;
            Success_Mode:= True;
         else
            Spark_IO.Put_Line(Spark_IO.Standard_Output,
                              "*** Mode (first letter) not valid. Should be O/M***",
                              0);
         end if;
         Route := Route_Left_Middle;
         if Item_2 = "LM"
         then
            Success_Route := True;
            Route := Route_Left_Middle;
         elsif Item_2 = "ML"
         then
            Success_Route := True;
            Route := Route_Middle_Left;
         elsif Item_2 = "RM"
         then
            Success_Route := True;
            Route := Route_Right_Middle;
         elsif Item_2 = "MR"
         then
            Success_Route := True;
            Route := Route_Middle_Right;
         elsif Item_2 = "LL"
         then
            Success_Route := True;
            Route := Route_Leave_Left;
         elsif Item_2 = "EL"
         then
            Success_Route := True;
            Route := Route_Enter_Left;
         elsif Item_2 = "LR"
         then
            Success_Route := True;
            Route := Route_Leave_Right;
         elsif Item_2 = "ER"
         then
            Success_Route := True;
            Route := Route_Enter_Right;
         else
            Success_Route:= False;
            Spark_IO.Put_Line(Spark_IO.Standard_Output,
                              "*** Route (letter 2 and 3) not valid ***",
                              0);
         end if;
         exit when (Success_Route and Success_Mode);
      end loop;
   end Get_Action;















   procedure Init is
      begin
         Signal_State := Signal_State_Type'(Leave_Left => Red,
                                            Enter_Left => Red,
                                              Left_Middle => Red,
                                              Middle_Left => Red,
                                              Middle_Right => Red,
                                              Right_Middle => Red,
                                              Leave_Right => Red,
                                              Enter_Right => Red);
         Segment_State := Segment_State_Type'(Left => Free,
                                                Middle => Free,
                                                Right  => Free);
      end Init;


end Simple_Railway;

