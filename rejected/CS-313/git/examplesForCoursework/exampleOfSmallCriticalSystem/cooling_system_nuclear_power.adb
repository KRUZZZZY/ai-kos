pragma SPARK_Mode (On);

with AS_IO_Wrapper;  use AS_IO_Wrapper; 


package body Cooling_System_Nuclear_Power is
   
   
   procedure Read_Temperature is
      Temperature : Integer;
   begin
      AS_Put_Line("Please type in current temperature as read by sensors");
      loop
         AS_Get(Temperature,"Please type in an integer");
         exit when (Temperature >=0) and (Temperature <= Maximum_Temperature_Possible);
         AS_Put("Please type in a value between 0 and ");
         AS_Put(Maximum_Temperature_Possible);
         AS_Put_Line("");
      end loop;
      Status_System.Temperature_Measured := Temperature_Range(Temperature);
   end Read_Temperature;
   
   function Status_Cooling_System_To_String (Status_Cooling_System   : Status_Cooling_System_Type) return String is
   begin
      -- it would be better to use a case construct
      -- since I didn't teach it I use here an if then else
      if (Status_Cooling_System = Activated) 
      then return "Activated";
      else return "Not_Activated";
      end if;
   end Status_Cooling_System_To_String;
	
   
   
   procedure Print_Status is
   begin
      AS_Put("Temperature = ");
      AS_Put(Integer(Status_System.Temperature_Measured));
      AS_Put_Line("");
      AS_Put("Cooling_System = ");
      AS_Put_Line(Status_Cooling_System_To_String(Status_System.Status_Cooling_System));
   end Print_Status;
   
   
   procedure Monitor_Cooling_System  is
   begin
      if Integer(Status_System.Temperature_Measured) > Critical_Temperature 
      then Status_System.Status_Cooling_System := Activated;
      else Status_System.Status_Cooling_System := Not_Activated;
      end if;
   end Monitor_Cooling_System;
   
   
   procedure Init is
   begin
      AS_Init_Standard_Input; 
      AS_Init_Standard_Output;
      Status_System := (Temperature_Measured  => 0,
                        Status_Cooling_System => Not_Activated);
   end Init;
   
   
      
     
end Cooling_System_Nuclear_Power;
	


