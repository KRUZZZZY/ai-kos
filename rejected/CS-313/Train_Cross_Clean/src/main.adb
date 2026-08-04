pragma SPARK_Mode (On);

with Level_Crossing; use Level_Crossing;

procedure Main is
begin
   Init;

   loop
      pragma Loop_Invariant (Is_Safe(Status_System));

      Read_Sensor_Status;

      for T in Train_ID loop
         pragma Loop_Invariant
           (for all P in Train_ID range 1 .. T - 1 =>
              Status_System.Trains(P).Distance <=
                Distance_Range(Maximum_Distance_Possible));

         Read_Train_Data(T);
      end loop;

      Monitor_Level_Crossing;
      Print_Status;

   end loop;
end Main;
