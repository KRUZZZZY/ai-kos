with SPARK.Text_IO;
with SPARK.Text_IO.Integer_IO;
with GCD_Verified_Contracts;

procedure Main is
   package Int_IO is new SPARK.Text_IO.Integer_IO (Integer);

   A, B : Integer := 0;
   G    : Integer := 0;
   GA   : Integer := 0;
   GB   : Integer := 0;

   Res     : Int_IO.Integer_Result;
   CharRes : SPARK.Text_IO.Character_Result;
   Ans     : Character := 'N';
begin
   SPARK.Text_IO.Init_Standard_Input;
   SPARK.Text_IO.Init_Standard_Output;
   SPARK.Text_IO.Init_Standard_Error;

   loop
      SPARK.Text_IO.Put_Line ("Compute gcd(a, b) with multipliers ga, gb (a, b > 0).");

      -- Read a
      loop
         SPARK.Text_IO.Put ("Enter a: ");
         Int_IO.Get (Res);
         case Res.Status is
            when SPARK.Text_IO.Success =>
               if Res.Item > 0 then
                  A := Res.Item;
                  exit;
               else
                  SPARK.Text_IO.Put_Line ("Number must be greater than 0. Try again.");
               end if;
            when SPARK.Text_IO.Data_Error =>
               SPARK.Text_IO.Put_Line ("Invalid number. Try again.");
               SPARK.Text_IO.Skip_Line;
            when SPARK.Text_IO.End_Error =>
               SPARK.Text_IO.Put_Line ("End of input while reading a.");
               exit;
            when others =>
               null;
         end case;
      end loop;

      -- Read b
      loop
         SPARK.Text_IO.Put ("Enter b: ");
         Int_IO.Get (Res);
         case Res.Status is
            when SPARK.Text_IO.Success =>
               if Res.Item > 0 then
                  B := Res.Item;
                  exit;
               else
                  SPARK.Text_IO.Put_Line ("Number must be greater than 0. Try again.");
               end if;
            when SPARK.Text_IO.Data_Error =>
               SPARK.Text_IO.Put_Line ("Invalid number. Try again.");
               SPARK.Text_IO.Skip_Line;
            when SPARK.Text_IO.End_Error =>
               SPARK.Text_IO.Put_Line ("End of input while reading b.");
               exit;
            when others =>
               null;
         end case;
      end loop;

      if A > 0 and B > 0 then
         -- Call verified gcd
         GCD_Verified_Contracts.Euclid_GCD_Verified
           (Positive(A), Positive(B), G, GA, GB);

         SPARK.Text_IO.Put ("gcd = "); Int_IO.Put (G); SPARK.Text_IO.New_Line;
         SPARK.Text_IO.Put ("ga  = "); Int_IO.Put (GA); SPARK.Text_IO.New_Line;
         SPARK.Text_IO.Put ("gb  = "); Int_IO.Put (GB); SPARK.Text_IO.New_Line;
      else
         SPARK.Text_IO.Put_Line ("Inputs must be positive (> 0). Try again.");
      end if;

      -- Ask to continue
      loop
         SPARK.Text_IO.Put ("Continue? (Y/N): ");
         SPARK.Text_IO.Get (CharRes);
         case CharRes.Status is
            when SPARK.Text_IO.Success =>
               Ans := CharRes.Item;
               if Ans = 'Y' or else Ans = 'y' or else Ans = 'N' or else Ans = 'n' then
                  exit;
               else
                  SPARK.Text_IO.Put_Line ("Please enter Y or N.");
                  SPARK.Text_IO.Skip_Line;
               end if;
            when SPARK.Text_IO.Data_Error =>
               SPARK.Text_IO.Put_Line ("Invalid character. Please enter Y or N.");
               SPARK.Text_IO.Skip_Line;
            when SPARK.Text_IO.End_Error =>
               SPARK.Text_IO.Put_Line ("End of input while reading answer.");
               exit;
            when others =>
               null;
         end case;
      end loop;

      exit when Ans = 'N' or else Ans = 'n';
      SPARK.Text_IO.New_Line;
   end loop;
end Main;
