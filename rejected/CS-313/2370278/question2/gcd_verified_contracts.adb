pragma SPARK_Mode;

package body GCD_Verified_Contracts with SPARK_Mode is

   procedure Euclid_GCD_Verified
     (A  : in  Positive;
      B  : in  Positive;
      G  : out Positive;
      GA : out Integer;
      GB : out Integer)
   is
      R  : Integer := Integer(A);
      S  : Integer := Integer(B);
      RA : Integer := 1;
      SA : Integer := 0;
      RB : Integer := 0;
      SB : Integer := 1;
      D  : Integer;
      R1 : Integer;
   begin
      while R /= 0 and S /= 0 loop
         pragma Loop_Invariant
           (Integer(A) = R * RA + S * SA
            and Integer(B) = R * RB + S * SB
            and ((R > 0 and S >= 0) or (S > 0 and R >= 0)));

         if R > S then
            D  := R / S;
            R1 := R mod S;
            pragma Assert (R = D * S + R1);
            SA := RA * D + SA;
            SB := RB * D + SB;
            R := R1;
         else
            D  := S / R;
            R1 := S mod R;
            pragma Assert (S = D * R + R1);
            RA := RA + SA * D;
            RB := RB + SB * D;
            S := R1;
         end if;

         pragma Assert
           (Integer(A) = R * RA + S * SA
            and Integer(B) = R * RB + S * SB
            and ((R > 0 and S >= 0) or (S > 0 and R >= 0)));
      end loop;

      if R = 0 then
         pragma Assert (S > 0);
         G  := Positive(S);
         GA := SA;
         GB := SB;
      else
         pragma Assert (R > 0);
         G  := Positive(R);
         GA := RA;
         GB := RB;
      end if;
   end Euclid_GCD_Verified;

end GCD_Verified_Contracts;
