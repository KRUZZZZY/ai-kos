pragma Spark_Mode (On);

package body GCD is

   procedure Euclid
     (A  : in  Integer;
      B  : in  Integer;
      G  : out Integer;
      Ga : out Integer;
      Gb : out Integer)
   is
      R  : Integer := A;
      S  : Integer := B;

      Ra : Integer := 1;
      Sa : Integer := 0;
      Rb : Integer := 0;
      Sb : Integer := 1;

      D  : Integer;
      R1 : Integer;
      S1 : Integer;
   begin

      -- Loop invariant enforced by asserts
      pragma Loop_Invariant (A = R * Ra + S * Sa);
      pragma Loop_Invariant (B = R * Rb + S * Sb);

      while R > 0 and S > 0 loop

         if R > S then
            D  := R / S;
            R1 := R mod S;
            pragma Assert (R = D * S + R1);

            R  := R1;
            Sa := Ra * D + Sa;
            Sb := Rb * D + Sb;

         elsif S > R then
            D  := S / R;
            S1 := S mod R;
            pragma Assert (S = D * R + S1);

            S  := S1;
            Ra := Ra + Sa * D;
            Rb := Rb + Sb * D;

         end if;

      end loop;

      pragma Assert ((R = 0 and S > 0) or (S = 0 and R > 0));

      if R > 0 then
         pragma Assert (S = 0);
         G  := R;
         Ga := Ra;
         Gb := Rb;
      else
         pragma Assert (R = 0);
         G  := S;
         Ga := Sa;
         Gb := Sb;
      end if;

   end Euclid;

end GCD;
