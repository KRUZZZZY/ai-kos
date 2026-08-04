with Spark_IO;
--# inherit Spark_IO;
package Simple_Railway
--# own Segment_State : Segment_State_Type;
--#     Signal_State  : Signal_State_Type;
is

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

   Segment_State : Segment_State_Type;
   Signal_State  : Signal_State_Type;



   procedure Open(Route: in Route_Type;
                        Success: out Boolean);
   --# global in out Segment_State, Signal_State;
   --# derives Segment_State,Success from
   --#         Segment_State, Route &
   --#         Signal_State  from
   --#         Segment_State, Route, Signal_State;

   --# pre (Signal_State.Middle_Left = Green
   --#          -> (Segment_State.Left = Reserved_Moving_From_Right
   --#              and Segment_State.Middle = Occupied_Moving_Left))
   --#      and
   --#     (Signal_State.Middle_Right = Green
   --#          -> (Segment_State.Right = Reserved_Moving_From_Left
   --#              and Segment_State.Middle = Occupied_Moving_Right))
   --#      and
   --#     (Signal_State.Left_Middle = Green
   --#          -> (Segment_State.Middle = Reserved_Moving_From_Left
   --#              and Segment_State.Left = Occupied_Moving_Right))
   --#      and
   --#     (Signal_State.Right_Middle = Green
   --#          -> (Segment_State.Middle = Reserved_Moving_From_Right
   --#              and Segment_State.Right = Occupied_Moving_Left))
   --#      and
   --#     (Signal_State.Leave_Left = Green
   --#          -> Segment_State.Left = Occupied_Moving_Left)
   --#
   --#      and
   --#     (Signal_State.Enter_Left = Green
   --#          -> Segment_State.Left = Reserved_Moving_From_Left)
   --#
   --#      and
   --#     (Signal_State.Leave_Right = Green
   --#          -> Segment_State.Right = Occupied_Moving_Right)
   --#
   --#      and
   --#     (Signal_State.Enter_Left = Green
   --#          -> Segment_State.Right = Reserved_Moving_From_Right);
   --#


   --# post (Signal_State.Middle_Left = Green
   --#          -> (Segment_State.Left = Reserved_Moving_From_Right
   --#              and Segment_State.Middle = Occupied_Moving_Left))
   --#      and
   --#     (Signal_State.Middle_Right = Green
   --#          -> (Segment_State.Right = Reserved_Moving_From_Left
   --#              and Segment_State.Middle = Occupied_Moving_Right))
   --#      and
   --#     (Signal_State.Left_Middle = Green
   --#          -> (Segment_State.Middle = Reserved_Moving_From_Left
   --#              and Segment_State.Left = Occupied_Moving_Right))
   --#      and
   --#     (Signal_State.Right_Middle = Green
   --#          -> (Segment_State.Middle = Reserved_Moving_From_Right
   --#              and Segment_State.Right = Occupied_Moving_Left))

   --#      and
   --#     (Signal_State.Leave_Left = Green
   --#          -> Segment_State.Left = Occupied_Moving_Left)
   --#
   --#      and
   --#     (Signal_State.Enter_Left = Green
   --#          -> Segment_State.Left = Reserved_Moving_From_Left)
   --#
   --#      and
   --#     (Signal_State.Leave_Right = Green
   --#          -> Segment_State.Right = Occupied_Moving_Right)
   --#
   --#      and
   --#     (Signal_State.Enter_Left = Green
   --#          -> Segment_State.Right = Reserved_Moving_From_Right)
   --#
   --#      and
   --#     ((Segment_State~.Left = Occupied_Moving_Left
   --#       or
   --#       Segment_State~.Left = Occupied_Moving_Right
   --#       or
   --#       Segment_State~.Left = Occupied_Standing)
   --#      ->
   --#     ((Segment_State.Left = Occupied_Moving_Left
   --#       or
   --#       Segment_State.Left = Occupied_Moving_Right
   --#       or
   --#       Segment_State.Left = Occupied_Standing)))
   --#      and
   --#     ((Segment_State~.Middle = Occupied_Moving_Left
   --#       or
   --#       Segment_State~.Middle = Occupied_Moving_Right
   --#       or
   --#       Segment_State~.Middle = Occupied_Standing)
   --#      ->
   --#     ((Segment_State.Middle = Occupied_Moving_Left
   --#       or
   --#       Segment_State.Middle = Occupied_Moving_Right
   --#       or
   --#       Segment_State.Middle = Occupied_Standing)))
   --#      and
   --#     ((Segment_State~.Right = Occupied_Moving_Left
   --#       or
   --#       Segment_State~.Right = Occupied_Moving_Right
   --#       or
   --#       Segment_State~.Right = Occupied_Standing)
   --#      ->
   --#     ((Segment_State.Right = Occupied_Moving_Left
   --#       or
   --#       Segment_State.Right = Occupied_Moving_Right
   --#       or
   --#       Segment_State.Right = Occupied_Standing)));

   procedure Move(Route: in Route_Type;
                        Success: out Boolean);
   --# global in out Segment_State, Signal_State;
   --# derives Signal_State,Segment_State,Success  from
   --#         Segment_State, Route, Signal_State;

   --# pre (Signal_State.Middle_Left = Green
   --#          -> (Segment_State.Left = Reserved_Moving_From_Right
   --#              and Segment_State.Middle = Occupied_Moving_Left))
   --#      and
   --#     (Signal_State.Middle_Right = Green
   --#          -> (Segment_State.Right = Reserved_Moving_From_Left
   --#              and Segment_State.Middle = Occupied_Moving_Right))
   --#      and
   --#     (Signal_State.Left_Middle = Green
   --#          -> (Segment_State.Middle = Reserved_Moving_From_Left
   --#              and Segment_State.Left = Occupied_Moving_Right))
   --#      and
   --#     (Signal_State.Right_Middle = Green
   --#          -> (Segment_State.Middle = Reserved_Moving_From_Right
   --#              and Segment_State.Right = Occupied_Moving_Left))
   --#      and
   --#     (Signal_State.Leave_Left = Green
   --#          -> Segment_State.Left = Occupied_Moving_Left)
   --#
   --#      and
   --#     (Signal_State.Enter_Left = Green
   --#          -> Segment_State.Left = Reserved_Moving_From_Left)
   --#
   --#      and
   --#     (Signal_State.Leave_Right = Green
   --#          -> Segment_State.Right = Occupied_Moving_Right)
   --#
   --#      and
   --#     (Signal_State.Enter_Left = Green
   --#          -> Segment_State.Right = Reserved_Moving_From_Right);
   --#


   --# post (Signal_State.Middle_Left = Green
   --#          -> (Segment_State.Left = Reserved_Moving_From_Right
   --#              and Segment_State.Middle = Occupied_Moving_Left))
   --#      and
   --#     (Signal_State.Middle_Right = Green
   --#          -> (Segment_State.Right = Reserved_Moving_From_Left
   --#              and Segment_State.Middle = Occupied_Moving_Right))
   --#      and
   --#     (Signal_State.Left_Middle = Green
   --#          -> (Segment_State.Middle = Reserved_Moving_From_Left
   --#              and Segment_State.Left = Occupied_Moving_Right))
   --#      and
   --#     (Signal_State.Right_Middle = Green
   --#          -> (Segment_State.Middle = Reserved_Moving_From_Right
   --#              and Segment_State.Right = Occupied_Moving_Left))
   --#
   --#      and
   --#     (Signal_State.Leave_Left = Green
   --#          -> Segment_State.Left = Occupied_Moving_Left)
   --#
   --#      and
   --#     (Signal_State.Enter_Left = Green
   --#          -> Segment_State.Left = Reserved_Moving_From_Left)
   --#
   --#      and
   --#     (Signal_State.Leave_Right = Green
   --#          -> Segment_State.Right = Occupied_Moving_Right)
   --#
   --#      and
   --#     (Signal_State.Enter_Left = Green
   --#          -> Segment_State.Right = Reserved_Moving_From_Right)
   --#
   --#      and
   --#      (Segment_State~.Left = Occupied_Moving_Right
   --#       ->
   --#       (Segment_State.Left = Occupied_Moving_Right
   --#        or
   --#       (Route = Route_Left_Middle
   --#        and Segment_State~.Middle = Reserved_Moving_From_Right
   --#        and Segment_State.Left = Free
   --#        and Segment_State.Middle = Occupied_Standing)))
   --#      and
   --#      (Segment_State~.Left = Occupied_Standing
   --#       ->
   --#       Segment_State.Left = Occupied_Standing)
   --#      and
   --#      (Segment_State~.Left = Occupied_Moving_Left
   --#       ->
   --#       (Segment_State.Left = Occupied_Moving_Left
   --#        or
   --#       (Route = Route_Leave_Left
   --#        and Segment_State.Left = Free)))
   --#
   --#      and
   --#      (Segment_State~.Middle = Occupied_Moving_Right
   --#       ->
   --#       (Segment_State.Middle = Occupied_Moving_Right
   --#        or
   --#       (Segment_State~.Right = Reserved_Moving_From_Left
   --#        and
   --#        Segment_State.Middle = Free and
   --#        Segment_State.Right = Occupied_Standing)))
   --#      and
   --#      (Segment_State~.Middle = Occupied_Moving_Left
   --#       ->
   --#       (Segment_State.Middle = Occupied_Moving_Left
   --#        or
   --#       (Segment_State~.Left = Reserved_Moving_From_Right
   --#        and
   --#        Segment_State.Middle = Free and
   --#        Segment_State.Left = Occupied_Standing)))
   --#      and
   --#      (Segment_State~.Middle = Occupied_Standing
   --#       ->
   --#       Segment_State.Middle = Occupied_Standing)
   --#
   --#      and
   --#      (Segment_State~.Right = Occupied_Moving_Left
   --#       ->
   --#       (Segment_State.Right = Occupied_Moving_Left
   --#        or
   --#       (Segment_State~.Middle = Reserved_Moving_From_Right
   --#        and Segment_State.Right = Free
   --#        and Segment_State.Middle = Occupied_Standing)))
   --#      and
   --#      (Segment_State~.Left = Occupied_Standing
   --#       ->
   --#       Segment_State.Left = Occupied_Standing);





   procedure Init;
   --# global out Segment_State, Signal_State;
   --# derives Segment_State, Signal_State from ;


   --# post (Signal_State.Middle_Left = Green
   --#          -> (Segment_State.Left = Reserved_Moving_From_Right
   --#              and Segment_State.Middle = Occupied_Moving_Left))
   --#      and
   --#     (Signal_State.Middle_Right = Green
   --#          -> (Segment_State.Right = Reserved_Moving_From_Left
   --#              and Segment_State.Middle = Occupied_Moving_Right))
   --#      and
   --#     (Signal_State.Left_Middle = Green
   --#          -> (Segment_State.Middle = Reserved_Moving_From_Left
   --#              and Segment_State.Left = Occupied_Moving_Right))
   --#      and
   --#     (Signal_State.Right_Middle = Green
   --#          -> (Segment_State.Middle = Reserved_Moving_From_Right
   --#              and Segment_State.Right = Occupied_Moving_Left))
   --#
   --#      and
   --#     (Signal_State.Leave_Left = Green
   --#          -> Segment_State.Left = Occupied_Moving_Left)
   --#
   --#      and
   --#     (Signal_State.Enter_Left = Green
   --#          -> Segment_State.Left = Reserved_Moving_From_Left)
   --#
   --#      and
   --#     (Signal_State.Leave_Right = Green
   --#          -> Segment_State.Right = Occupied_Moving_Right)
   --#
   --#      and
   --#     (Signal_State.Enter_Left = Green
   --#          -> Segment_State.Right = Reserved_Moving_From_Right);
   --#
   --#

procedure Print_One_Signal(The_Signal_State: in One_Signal_State);
   --# global in out Spark_IO.Outputs;
   --# derives Spark_IO.Outputs from Spark_IO.Outputs, The_Signal_State;

procedure Print_One_Segment_State(the_State: in One_Segment_State);
   --# global in out Spark_IO.Outputs;
   --# derives Spark_IO.Outputs from Spark_IO.Outputs, The_State;

procedure Print_State;
   --# global in out Spark_IO.Outputs;
   --#        in Segment_State, Signal_State;
   --# derives Spark_IO.Outputs from Spark_IO.Outputs,  Segment_State,
   --#         Signal_State;



procedure Get_Action(Route: out Route_Type;
                     The_Mode : out Mode);
 --# global in out Spark_IO.Inputs, Spark_IO.Outputs;
 --# derives Spark_IO.Outputs from Spark_IO.Outputs, Spark_IO.Inputs &
 --#         Spark_IO.Inputs, Route, The_Mode from Spark_IO.Inputs ;









end Simple_Railway;
