-- this is the executable file 
-- running the nuclear power system
--
-- it initialises the system
-- then runs for ever in a loop which
--   1) reads the temperature from console
--   2) monitors the cooling system so that the cooling
--      system is activated if the temperature is too high
--   3) prints out the status
-- 
--  the loop_invariant expresses that the system stays safe all the time.

pragma SPARK_Mode (On);

with Cooling_System_Nuclear_Power;
use Cooling_System_Nuclear_Power;



procedure Main
is
begin
   Init;
   loop
      pragma Loop_Invariant (Is_Safe(Status_System));
      Read_Temperature;
      Monitor_Cooling_System;
      Print_Status;
   end loop;
end Main;

      
