pragma SPARK_Mode (On);

with AS_Io_Wrapper; use AS_Io_Wrapper;
with Clock;        use Clock;

procedure Main is
   Month_Input : String (1 .. 10);
   Last : Natural;
   Date_Input : Date;
   Completed : Boolean;
   Temp_Day : Integer;
   Day_Func : Year_Days;
   Day_Proc : Year_Days;
   Answer : String (1 .. 10);
   Answer_Last : Natural;

begin
   AS_Init_Standard_Input;
   AS_Init_Standard_Output;

   loop
      loop
         AS_Put_Line ("Enter the 3 letter abbreviation of any month (e.g. jan): ");
         AS_Get_Line (Month_Input, Last);

         If Last > Month_Input'Last then
            Last := Month_Input'Last;
         end if;

         if Last = 3 then
            String_To_Month (Month_Input (1 .. Last), Completed, Date_Input.M);
            exit when Completed;
         end if;

         AS_Put_Line("Invalid month, try again.");
      end loop;

      loop
         AS_Put_Line ("Enter a day from 1 to 31.");
         AS_Get (Temp_Day);

         if not (Temp_Day in Month_Days) then
            AS_Put_Line ("Months can only have between 1 and 31 days.");
         else
            Date_Input.D := Month_Days (Temp_Day);
            if Valid_Input (Date_Input) then
               exit;
            else
               AS_Put_Line("The month you selected doesn't have that many days.");
            end if;
         end if;
      end loop;


      Day_Func := Accumulated_Days (Date_Input);
      Accumulated_Days_Proc (Date_Input, Day_Proc);

      AS_Put ("Day of year function: ");
      AS_Put_Line (Integer (Day_Func));

      AS_Put ("Day of year procedure: ");
      AS_Put_Line (Integer (Day_Proc));

      AS_Put("Would you like to continue?");
      AS_Get_Line (Answer, Answer_Last);

      if Answer_Last > 0 then
         if Answer (1) = 'n' or Answer (1) = 'N' then
            exit;
         end if;
      end if;
   end loop;
end Main;


