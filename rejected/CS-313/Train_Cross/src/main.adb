pragma SPARK_Mode (On);

with Level_Crossing;
use Level_Crossing;

-- ============================================================================
-- Main Control Loop for Railway Level Crossing System
-- ============================================================================
-- This is the top-level control loop that continuously monitors the crossing.
-- Each iteration:
--   1. Checks sensor health status
--   2. Reads data for all tracked trains
--   3. Applies safety logic to determine barrier state
--   4. Displays current system status
--
-- The loop invariant ensures that after every iteration, the system maintains
-- its fundamental safety property: barriers are down whenever required.
--
-- Non-linear danger distance calculation: 800m + (speed^2 / 2)
-- This reflects the physics principle that kinetic energy (and thus stopping
-- distance) increases with the square of velocity.
-- ============================================================================

procedure Main is
begin
   -- Initialize system to known safe state
   Init;

   -- Main monitoring loop - runs continuously
   loop
      -- SAFETY INVARIANT: System must be in a safe state at start of each iteration
      -- This is guaranteed because:
      --   - Init establishes Is_Safe initially
      --   - Monitor_Level_Crossing re-establishes Is_Safe at end of each iteration
      pragma Loop_Invariant (Is_Safe(Status_System));
      pragma Loop_Invariant (All_Distances_Valid(Status_System));
      pragma Loop_Invariant (All_Speeds_Valid(Status_System));

      -- Step 1: Check sensor health (fail-safe: faults force barriers down)
      -- Note: This may temporarily violate Is_Safe until Monitor_Level_Crossing runs
      Read_Sensor_Status;

      -- Step 2: Read information about all trains being monitored
      -- Note: Data collection phase may temporarily violate Is_Safe
      for T in Train_ID loop
         -- Maintain data validity invariants during collection
         pragma Loop_Invariant (All_Distances_Valid(Status_System));
         pragma Loop_Invariant (All_Speeds_Valid(Status_System));
         pragma Loop_Invariant
           (for all Checked in Train_ID range 1 .. T - 1 =>
             Status_System.Trains(Checked).Distance <=
               Distance_Range(Maximum_Distance_Possible));
         -- Sensor fault status doesn't change during train data collection
         pragma Loop_Invariant
           (Status_System.Sensor_Fault = Status_System.Sensor_Fault'Loop_Entry);

         Read_Train_Data(T);
      end loop;

      -- Step 3: Apply safety-critical monitoring logic
      -- This analyzes all inputs and determines the correct barrier state
      -- CRITICAL: This procedure re-establishes Is_Safe for the next iteration
      Monitor_Level_Crossing;

      -- Step 4: Display current status to operator
      Print_Status;

      -- Loop continues indefinitely for continuous monitoring
      -- Is_Safe is guaranteed here by Monitor_Level_Crossing postcondition
   end loop;
end Main;
