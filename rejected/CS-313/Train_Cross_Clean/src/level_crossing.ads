pragma SPARK_Mode (On);

with SPARK.Text_IO; use SPARK.Text_IO;

-- Level crossing controller for 3-train monitoring system
-- Implements fail-safe barrier control based on UK railway standards
package Level_Crossing is

   -- System configuration
   Maximum_Distance_Possible : constant Integer := 10000;  -- 10km tracking range
   Base_Danger_Distance : constant Integer := 800;         -- Base closure distance
   Max_Train_Speed : constant Natural := 56;               -- ~200 km/h
   Number_Of_Trains : constant := 3;

   type Distance_Range is new Integer range 0 .. Maximum_Distance_Possible;
   type Speed_Range is new Natural range 0 .. Max_Train_Speed;
   type Barrier_State_Type is (Barrier_Down, Barrier_Up);
   type Train_ID is range 1 .. Number_Of_Trains;

   type Train_Info is record
      Distance   : Distance_Range;
      Speed      : Speed_Range;
      Is_Present : Boolean;
   end record;

   type Train_Array is array (Train_ID) of Train_Info;

   type Status_System_Type is record
      Trains        : Train_Array;
      Barrier_State : Barrier_State_Type;
      Sensor_Fault  : Boolean;
   end record;

   Status_System : Status_System_Type :=
     (Trains => (others => (Distance => Distance_Range(Maximum_Distance_Possible),
                            Speed => 0,
                            Is_Present => False)),
      Barrier_State => Barrier_Down,
      Sensor_Fault => False);

   -- Danger distance formula: 800 + v²/2
   -- Accounts for kinetic energy increase with speed
   function Calculate_Danger_Distance (Speed : Speed_Range) return Natural is
     (Base_Danger_Distance + (Natural(Speed) * Natural(Speed)) / 2)
   with Post => Calculate_Danger_Distance'Result >= Base_Danger_Distance and
                Calculate_Danger_Distance'Result <= Base_Danger_Distance +
                  (Max_Train_Speed * Max_Train_Speed) / 2;

   function Any_Train_In_Danger_Zone (Trains : Train_Array) return Boolean is
     (for some T in Train_ID =>
       (Trains(T).Is_Present and then
        Integer(Trains(T).Distance) <=
          Calculate_Danger_Distance(Trains(T).Speed)));

   function Safety_Margin (Train : Train_Info) return Integer is
     (Integer(Train.Distance) - Calculate_Danger_Distance(Train.Speed))
   with Pre => Train.Is_Present;

   function Time_To_Crossing (Train : Train_Info) return Natural is
     (if Train.Speed = 0 then 999999
      else Natural(Train.Distance) / Natural(Train.Speed))
   with Pre => Train.Is_Present;

   function All_Distances_Valid (Status : Status_System_Type) return Boolean is
     (for all T in Train_ID =>
         Status.Trains(T).Distance <= Distance_Range(Maximum_Distance_Possible));

   function All_Speeds_Valid (Status : Status_System_Type) return Boolean is
     (for all T in Train_ID =>
         Status.Trains(T).Speed <= Speed_Range(Max_Train_Speed));

   -- Core safety invariant:
   -- - Sensor fault OR train in danger zone => barriers down
   -- - No faults AND no danger => barriers up
   function Is_Safe (Status : Status_System_Type) return Boolean is
     (((not Status.Sensor_Fault) or (Status.Barrier_State = Barrier_Down)) and
      ((not Any_Train_In_Danger_Zone(Status.Trains)) or
       (Status.Barrier_State = Barrier_Down)) and
      ((Status.Sensor_Fault or Any_Train_In_Danger_Zone(Status.Trains))
       or (Status.Barrier_State = Barrier_Up)))
   with Post => Is_Safe'Result =
     (((not Status.Sensor_Fault) or (Status.Barrier_State = Barrier_Down)) and
      ((not Any_Train_In_Danger_Zone(Status.Trains)) or
       (Status.Barrier_State = Barrier_Down)) and
      ((Status.Sensor_Fault or Any_Train_In_Danger_Zone(Status.Trains))
       or (Status.Barrier_State = Barrier_Up)));

   procedure Init with
     Global  => (Output => (Standard_Output, Standard_Input, Status_System)),
     Depends => ((Standard_Output, Standard_Input, Status_System) => null),
     Post    => Is_Safe(Status_System) and
                Status_System.Barrier_State = Barrier_Up and
                not Status_System.Sensor_Fault and
                (for all T in Train_ID =>
                  Status_System.Trains(T).Distance =
                    Distance_Range(Maximum_Distance_Possible) and
                  Status_System.Trains(T).Speed = 0 and
                  not Status_System.Trains(T).Is_Present) and
                All_Distances_Valid(Status_System) and
                All_Speeds_Valid(Status_System);

   procedure Read_Sensor_Status with
     Global  => (In_Out => (Standard_Output, Standard_Input, Status_System)),
     Depends => (Standard_Output => (Standard_Output, Standard_Input),
                 Standard_Input  => Standard_Input,
                 Status_System   => (Status_System, Standard_Input)),
     Post    => (for all T in Train_ID =>
                  Status_System.Trains(T) = Status_System.Trains'Old(T)) and
                Status_System.Barrier_State = Status_System.Barrier_State'Old and
                All_Distances_Valid(Status_System) and
                All_Speeds_Valid(Status_System);

   procedure Read_Train_Data (Train_Number : Train_ID) with
     Global  => (In_Out => (Standard_Output, Standard_Input, Status_System)),
     Depends => (Standard_Output => (Standard_Output, Standard_Input, Train_Number, Status_System),
                 Standard_Input  => (Standard_Input, Train_Number, Status_System),
                 Status_System   => (Status_System, Standard_Input, Train_Number)),
     Post    => Status_System.Trains(Train_Number).Distance <=
                  Distance_Range(Maximum_Distance_Possible) and
                Status_System.Trains(Train_Number).Speed <=
                  Speed_Range(Max_Train_Speed) and
                (for all T in Train_ID =>
                  (if T /= Train_Number then
                    Status_System.Trains(T) = Status_System.Trains'Old(T))) and
                Status_System.Sensor_Fault = Status_System.Sensor_Fault'Old and
                Status_System.Barrier_State = Status_System.Barrier_State'Old and
                All_Distances_Valid(Status_System) and
                All_Speeds_Valid(Status_System);

   -- Main barrier control logic
   procedure Monitor_Level_Crossing with
     Global  => (In_Out => Status_System),
     Depends => (Status_System => Status_System),
     Post    => Is_Safe(Status_System) and
                (if Status_System.Sensor_Fault then
                   Status_System.Barrier_State = Barrier_Down) and
                (if Any_Train_In_Danger_Zone(Status_System.Trains) then
                   Status_System.Barrier_State = Barrier_Down) and
                (if not Status_System.Sensor_Fault and
                    not Any_Train_In_Danger_Zone(Status_System.Trains) then
                   Status_System.Barrier_State = Barrier_Up) and
                Status_System.Trains = Status_System.Trains'Old and
                Status_System.Sensor_Fault = Status_System.Sensor_Fault'Old and
                All_Distances_Valid(Status_System) and
                All_Speeds_Valid(Status_System);

   procedure Print_Status with
     Global  => (In_Out => Standard_Output,
                 Input   => Status_System),
     Depends => (Standard_Output => (Standard_Output, Status_System));

   function Barrier_State_To_String (Barrier_State : Barrier_State_Type)
     return String;

   function Boolean_To_String (Value : Boolean) return String;

end Level_Crossing;
