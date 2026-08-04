-- This file was created by Anton Setzer
-- it is an ultra simple example of a critical system
-- namely the cooling system of a nuclear power station.
-- if the temperature goes above a critical value
-- the cooling system will be set to activated.

pragma SPARK_Mode (On);

with SPARK.Text_IO;use  SPARK.Text_IO;


package Cooling_System_Nuclear_Power is
   
   -- Maximum_Temperature_Possible describes the 
   -- maximum temperature which could ever occur when runnin
   -- this system (even in case of an accident)
   -- it is needed since we restrict the integers up to this value.
   
   Maximum_Temperature_Possible : constant Integer := 10000;
   
   -- if the temperature exceeds Critical_Temperature
   -- then the cooling system will be activated
   Critical_Temperature : constant Integer := 5000;
   
   -- range of temperatures which possible can exist
   type Temperature_Range is new Integer range 0 .. Maximum_Temperature_Possible;
   
   -- status of the cooling system
   type Status_Cooling_System_Type is (Activated, Not_Activated);
   
   -- status of the overall system consisting of the temperature and the status of the cooling system
   type Status_System_Type  is 
      record
         Temperature_Measured   : Temperature_Range;
         Status_Cooling_System : Status_Cooling_System_Type;
      end record;
   
   -- Status System is a global variable determining the status of the system
   Status_System : Status_System_Type;
   
   -- Read_Temperature gets the current temperature from console input output
   -- and updates Status_System
   -- it does NOT monitor the cooling system
   -- so after executing it the system might be unsafe.x
   procedure Read_Temperature with
     Global => (In_Out => (Standard_Output, Standard_Input,Status_System)),
     Depends => (Standard_Output => (Standard_Output,Standard_Input),
                 Standard_Input  => Standard_Input,
                 Status_System   => (Status_System, Standard_Input));
   
   -- This function converts a value into Status_Cooling_System_Type
   -- into a string which can be printed to console
   function Status_Cooling_System_To_String (Status_Cooling_System   : Status_Cooling_System_Type) return String;
      
   
   
   -- Print Status prints out the status of the system on console
   procedure Print_Status with
     Global => (In_Out => Standard_Output, 
                Input  => Status_System),
     Depends => (Standard_Output => (Standard_Output,Status_System));
   
   
   -- Is_Safe determines whether the system is safe, if applied to Status_System
   -- This is an example of an expression function
   -- It abbreviates in verification condition what it means for the system to be safe.
   -- Is_Safe(Status_System) means that the system is safe
   
   function Is_Safe (Status : Status_System_Type) return Boolean is
     (if Integer(Status.Temperature_Measured) > Critical_Temperature 
      then Status.Status_Cooling_System = Activated
      else Status.Status_Cooling_System = Not_Activated);

   
   
   -- Monitor_Cooling_System monitors the temperature; if it is too high
   -- it activates the cooling system if the temperature is higher than the critical temperature
   -- Afterwards the system will be safe as expressed by  the post condition
   
   procedure Monitor_Cooling_System  with
     Global  => (In_Out => Status_System),
     Depends => (Status_System => Status_System),
     Post    => Is_Safe(Status_System);
	      
   -- Init initialises the system to some values.
   -- afterwards the system is safe.x
   procedure Init with
     Global => (Output => (Standard_Output,Standard_Input,Status_System)),
     Depends => ((Standard_Output,Standard_Input,Status_System) => null),
     Post    => Is_Safe(Status_System);
   
   

     
     
   
   
   
   
end  Cooling_System_Nuclear_Power;


