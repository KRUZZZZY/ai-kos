pragma SPARK_Mode (On);

with AS_IO_Wrapper; use AS_IO_Wrapper;

package body Level_Crossing is

   procedure Init is
   begin
      AS_Init_Standard_Input;
      AS_Init_Standard_Output;

      Status_System.Barrier_State := Barrier_Up;
      Status_System.Sensor_Fault := False;

      for T in Train_ID loop
         Status_System.Trains(T).Distance :=
           Distance_Range(Maximum_Distance_Possible);
         Status_System.Trains(T).Speed := 0;
         Status_System.Trains(T).Is_Present := False;
      end loop;

      AS_Put_Line("===========================================");
      AS_Put_Line("Railway Level Crossing Control System v2.0");
      AS_Put_Line("===========================================");
      AS_Put_Line("Monitoring " & Integer'Image(Number_Of_Trains) & " trains");
      AS_Put_Line("Base danger distance: " &
                  Integer'Image(Base_Danger_Distance) & "m");
      AS_Put_Line("Danger formula: Base + (Speed^2 / 2)");
      AS_Put_Line("Max train speed: " & Integer'Image(Max_Train_Speed) & " m/s");
      AS_Put_Line("===========================================");
      AS_Put_Line("");
   end Init;

   procedure Read_Sensor_Status is
      Fault_Input : Integer;
   begin
      AS_Put_Line("");
      AS_Put_Line("--- SENSOR STATUS CHECK ---");
      AS_Put("Are sensors functioning correctly? (1=Yes, 0=No/Fault): ");

      loop
         AS_Get(Fault_Input, "Please enter 1 for Yes or 0 for Fault");
         exit when (Fault_Input = 0) or (Fault_Input = 1);
         AS_Put_Line("Invalid input. Enter 1 (sensors OK) or 0 (fault detected)");
      end loop;

      Status_System.Sensor_Fault := (Fault_Input = 0);

      if Status_System.Sensor_Fault then
         AS_Put_Line("*** SENSOR FAULT DETECTED - FAIL-SAFE MODE ***");
      else
         AS_Put_Line("Sensors operational.");
      end if;
   end Read_Sensor_Status;

   procedure Read_Train_Data (Train_Number : Train_ID) is
      Present_Input : Integer;
      Distance      : Integer;
      Speed         : Integer;
   begin
      AS_Put_Line("");
      AS_Put_Line("--- TRAIN " & Train_ID'Image(Train_Number) & " DATA ---");

      AS_Put("Is Train " & Train_ID'Image(Train_Number) &
             " present? (1=Yes, 0=No): ");
      loop
         AS_Get(Present_Input, "Please enter 1 for Yes or 0 for No");
         exit when (Present_Input = 0) or (Present_Input = 1);
         AS_Put_Line("Invalid input. Enter 1 (present) or 0 (not present)");
      end loop;

      Status_System.Trains(Train_Number).Is_Present := (Present_Input = 1);

      if Status_System.Trains(Train_Number).Is_Present then
         AS_Put("Distance from crossing (0-" &
                Integer'Image(Maximum_Distance_Possible) & " meters): ");
         loop
            AS_Get(Distance, "Please enter a valid distance");
            exit when (Distance >= 0) and
                      (Distance <= Maximum_Distance_Possible);
            AS_Put("Distance must be between 0 and ");
            AS_Put(Maximum_Distance_Possible);
            AS_Put_Line(" meters");
         end loop;
         Status_System.Trains(Train_Number).Distance := Distance_Range(Distance);

         AS_Put("Train speed (0-" & Integer'Image(Max_Train_Speed) &
                " m/s): ");
         loop
            AS_Get(Speed, "Please enter a valid speed");
            exit when (Speed >= 0) and (Speed <= Max_Train_Speed);
            AS_Put("Speed must be between 0 and ");
            AS_Put(Max_Train_Speed);
            AS_Put_Line(" m/s");
         end loop;
         Status_System.Trains(Train_Number).Speed := Speed_Range(Speed);

         declare
            Danger_Dist : constant Natural :=
              Calculate_Danger_Distance(Status_System.Trains(Train_Number).Speed);
         begin
            AS_Put("  -> Danger distance for this speed: ");
            AS_Put(Danger_Dist);
            AS_Put_Line("m");

            if Integer(Status_System.Trains(Train_Number).Distance) <= Danger_Dist then
               AS_Put_Line("  -> *** TRAIN IN DANGER ZONE ***");
            else
               AS_Put_Line("  -> Train at safe distance");
            end if;
         end;
      else
         Status_System.Trains(Train_Number).Distance :=
           Distance_Range(Maximum_Distance_Possible);
         Status_System.Trains(Train_Number).Speed := 0;
         AS_Put_Line("Train not present - marked as clear");
      end if;
   end Read_Train_Data;

   procedure Monitor_Level_Crossing is
      Must_Close_Barrier : Boolean := False;
   begin
      -- Fail-safe: any sensor fault forces barriers down
      if Status_System.Sensor_Fault then
         Must_Close_Barrier := True;
      end if;

      -- Check each train against its danger zone
      for T in Train_ID loop
         if Status_System.Trains(T).Is_Present then
            declare
               Train_Danger_Distance : constant Natural :=
                 Calculate_Danger_Distance(Status_System.Trains(T).Speed);
            begin
               if Integer(Status_System.Trains(T).Distance) <=
                  Train_Danger_Distance then
                  Must_Close_Barrier := True;
               end if;
            end;
         end if;
      end loop;

      if Must_Close_Barrier then
         Status_System.Barrier_State := Barrier_Down;
      else
         Status_System.Barrier_State := Barrier_Up;
      end if;
   end Monitor_Level_Crossing;

   procedure Print_Status is
   begin
      AS_Put_Line("");
      AS_Put_Line("===========================================");
      AS_Put_Line("        CURRENT SYSTEM STATUS");
      AS_Put_Line("===========================================");

      AS_Put("Sensor Status: ");
      if Status_System.Sensor_Fault then
         AS_Put_Line("*** FAULT DETECTED ***");
      else
         AS_Put_Line("Operational");
      end if;

      AS_Put_Line("");

      for T in Train_ID loop
         AS_Put("Train ");
         AS_Put(Integer(T));
         AS_Put(": ");

         if Status_System.Trains(T).Is_Present then
            AS_Put("PRESENT - Distance: ");
            AS_Put(Integer(Status_System.Trains(T).Distance));
            AS_Put("m, Speed: ");
            AS_Put(Integer(Status_System.Trains(T).Speed));
            AS_Put("m/s");

            declare
               Danger_Dist : constant Natural :=
                 Calculate_Danger_Distance(Status_System.Trains(T).Speed);
            begin
               AS_Put(" (Danger zone: ");
               AS_Put(Danger_Dist);
               AS_Put("m)");

               if Integer(Status_System.Trains(T).Distance) <= Danger_Dist then
                  AS_Put(" *** IN DANGER ZONE ***");
               end if;
            end;
            AS_Put_Line("");
         else
            AS_Put_Line("Not present");
         end if;
      end loop;

      AS_Put_Line("");
      AS_Put_Line("-------------------------------------------");
      AS_Put("BARRIER STATE: ");
      AS_Put_Line(Barrier_State_To_String(Status_System.Barrier_State));

      if Status_System.Barrier_State = Barrier_Down then
         AS_Put_Line("  -> Road is CLOSED to traffic");
         AS_Put_Line("  -> Crossing is PROTECTED");
      else
         AS_Put_Line("  -> Road is OPEN to traffic");
         AS_Put_Line("  -> Normal operation");
      end if;

      AS_Put_Line("===========================================");
      AS_Put_Line("");
   end Print_Status;

   function Barrier_State_To_String (Barrier_State : Barrier_State_Type)
     return String is
   begin
      if Barrier_State = Barrier_Down then
         return "DOWN";
      else
         return "UP";
      end if;
   end Barrier_State_To_String;

   function Boolean_To_String (Value : Boolean) return String is
   begin
      if Value then
         return "Yes";
      else
         return "No";
      end if;
   end Boolean_To_String;

end Level_Crossing;
