pragma SPARK_Mode (On);

with SPARK.Text_IO; use SPARK.Text_IO;

-- ============================================================================
-- Level Crossing Safety-Critical Control System
-- ============================================================================
-- This package implements a railway level crossing controller that monitors
-- multiple trains and sensor health to ensure road barriers operate safely.
-- The system enforces the fundamental safety property: barriers must be down
-- whenever any train is within its danger distance or when sensor faults occur.
--
-- SAFETY RATIONALE:
-- This system follows the "Fail-Safe" principle used in railway engineering:
-- - Default state is SAFE (barriers down)
-- - Any uncertainty -> fail to safe state
-- - No single point of failure (multiple checks)
-- - Conservative danger distances (account for worst-case braking)
--
-- VERIFICATION APPROACH:
-- - Type system prevents invalid states
-- - Loop invariants prove safety maintained throughout execution
-- - Postconditions prove each operation preserves safety
-- - Is_Safe function expresses complete safety property
-- ============================================================================

package Level_Crossing is

   -- =========================================================================
   -- CONSTANTS AND TYPES
   -- =========================================================================

   -- Maximum distance at which we track trains (10 km monitoring range)
   Maximum_Distance_Possible : constant Integer := 10000;

   -- Base danger distance: barriers must be down if train is closer than 800m
   -- This allows approximately 65 seconds warning at typical freight speeds
   -- Based on UK law, most freight trains operate up to 120 km/h (33 m/s)
   -- Freight trains at 120 km/h typically require ~1500m to stop
   --
   -- PHYSICS RATIONALE:
   -- Kinetic Energy: KE = (1/2) * m * v²
   -- Braking force: F = m * a (deceleration)
   -- Stopping distance: d = v² / (2 * a)
   -- For freight trains: typical deceleration ~0.5 m/s²
   -- At 56 m/s: theoretical stopping distance = 56² / (2 * 0.5) = 3136m
   -- Base distance (800m) provides additional safety margin for reaction time
   Base_Danger_Distance : constant Integer := 800;

   -- Maximum realistic train speed we monitor (56 m/s roughly 200 km/h)
   Max_Train_Speed : constant Natural := 56;

   -- Number of trains we simultaneously track
   Number_Of_Trains : constant := 3;

   -- Valid distance range for train positions
   type Distance_Range is new Integer range 0 .. Maximum_Distance_Possible;

   -- Train speed in meters per second
   type Speed_Range is new Natural range 0 .. Max_Train_Speed;

   -- Barrier can be either down (safe, blocking road) or up (allowing traffic)
   type Barrier_State_Type is (Barrier_Down, Barrier_Up);

   -- Identifier for each train we're tracking
   type Train_ID is range 1 .. Number_Of_Trains;

   -- Complete information about a single train
   type Train_Info is record
      Distance   : Distance_Range;  -- Distance from crossing in meters
      Speed      : Speed_Range;     -- Current speed in m/s
      Is_Present : Boolean;         -- Whether this train is actively tracked
   end record;

   -- Array holding all trains we're monitoring
   type Train_Array is array (Train_ID) of Train_Info;

   -- System status including all trains, barrier state, and sensor health
   type Status_System_Type is record
      Trains        : Train_Array;
      Barrier_State : Barrier_State_Type;
      Sensor_Fault  : Boolean;  -- True if any sensor is malfunctioning
   end record;

   -- Global system status variable - initialized to safe state
   Status_System : Status_System_Type :=
     (Trains => (others => (Distance => Distance_Range(Maximum_Distance_Possible),
                            Speed => 0,
                            Is_Present => False)),
      Barrier_State => Barrier_Down,  -- Fail-safe default
      Sensor_Fault => False);

   -- =========================================================================
   -- SAFETY-CRITICAL FUNCTIONS
   -- =========================================================================

   -- Calculate the required danger distance for a train based on its speed
   -- Uses physics principle: stopping distance increases with square of velocity
   -- Formula: 800m base + speed²/2
   -- Example: 50 m/s train needs 800 + 2500/2 = 2,050m danger distance
   -- Example: 20 m/s train needs 800 + 400/2 = 1,000m danger distance
   -- Example: 0 m/s train needs 800m (base only)
   function Calculate_Danger_Distance (Speed : Speed_Range) return Natural is
     (Base_Danger_Distance + (Natural(Speed) * Natural(Speed)) / 2)
   with Post => Calculate_Danger_Distance'Result >= Base_Danger_Distance and
                Calculate_Danger_Distance'Result <= Base_Danger_Distance +
                  (Max_Train_Speed * Max_Train_Speed) / 2;

   -- Check if any monitored train requires barriers to be down
   -- Returns true if at least one present train is in its danger zone
   function Any_Train_In_Danger_Zone (Trains : Train_Array) return Boolean is
     (for some T in Train_ID =>
       (Trains(T).Is_Present and then
        Integer(Trains(T).Distance) <=
          Calculate_Danger_Distance(Trains(T).Speed)));

   -- Calculate safety margin for a train (positive = safe, negative = danger)
   -- This is the distance beyond the danger zone
   function Safety_Margin (Train : Train_Info) return Integer is
     (Integer(Train.Distance) - Calculate_Danger_Distance(Train.Speed))
   with Pre => Train.Is_Present;

   -- Calculate time until train reaches crossing (seconds)
   -- Returns large value if train is stationary
   function Time_To_Crossing (Train : Train_Info) return Natural is
     (if Train.Speed = 0 then 999999
      else Natural(Train.Distance) / Natural(Train.Speed))
   with Pre => Train.Is_Present;

   -- Verify all train distances are within valid range
   function All_Distances_Valid (Status : Status_System_Type) return Boolean is
     (for all T in Train_ID =>
         Status.Trains(T).Distance <= Distance_Range(Maximum_Distance_Possible));

   -- Verify all train speeds are within valid range
   function All_Speeds_Valid (Status : Status_System_Type) return Boolean is
     (for all T in Train_ID =>
         Status.Trains(T).Speed <= Speed_Range(Max_Train_Speed));

   -- Primary safety property: system is safe if barriers are correctly positioned
   -- Barriers MUST be down if:
   --   1. Any sensor fault is detected (fail-safe principle), OR
   --   2. Any present train is within its speed-dependent danger distance
   -- Otherwise, barriers should be up to allow normal road traffic flow
   --
   -- CORRECTED LOGIC: Uses boolean operators to express implications:
   --   1. Sensor fault implies barriers down: (not Fault) or (Barriers Down)
   --   2. Train in danger implies barriers down: (not Danger) or (Barriers Down)
   --   3. No faults and no danger implies barriers up: (Fault or Danger) or (Barriers Up)
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

   -- =========================================================================
   -- SYSTEM PROCEDURES
   -- =========================================================================

   -- Initialize the system to a known safe state
   -- All trains set to maximum distance, barriers up, no faults
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

   -- Read sensor fault status from operator input
   -- In a real system, this would be automatic sensor monitoring
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

   -- Read information about a specific train from operator input
   -- Prompts for: presence, distance, and speed
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

   -- Main safety logic: determine correct barrier state based on all inputs
   -- This is the critical safety function that enforces the protection policy
   procedure Monitor_Level_Crossing with
     Global  => (In_Out => Status_System),
     Depends => (Status_System => Status_System),
     Post    => Is_Safe(Status_System) and
                -- Barriers must be down if sensor fault detected
                (if Status_System.Sensor_Fault then
                   Status_System.Barrier_State = Barrier_Down) and
                -- Barriers must be down if any train in danger zone
                (if Any_Train_In_Danger_Zone(Status_System.Trains) then
                   Status_System.Barrier_State = Barrier_Down) and
                -- Barriers should be up only if no faults and no trains in danger
                (if not Status_System.Sensor_Fault and
                    not Any_Train_In_Danger_Zone(Status_System.Trains) then
                   Status_System.Barrier_State = Barrier_Up) and
                -- Train data is never modified by monitoring
                Status_System.Trains = Status_System.Trains'Old and
                Status_System.Sensor_Fault = Status_System.Sensor_Fault'Old and
                All_Distances_Valid(Status_System) and
                All_Speeds_Valid(Status_System);

   -- Display current system status to operator console
   -- Now includes risk analysis with safety margins and time-to-crossing
   procedure Print_Status with
     Global  => (In_Out => Standard_Output,
                 Input   => Status_System),
     Depends => (Standard_Output => (Standard_Output, Status_System));

   -- =========================================================================
   -- UTILITY FUNCTIONS
   -- =========================================================================

   -- Convert barrier state enum to human-readable string
   function Barrier_State_To_String (Barrier_State : Barrier_State_Type)
     return String;

   -- Convert boolean to Yes/No string for display
   function Boolean_To_String (Value : Boolean) return String;

end Level_Crossing;
