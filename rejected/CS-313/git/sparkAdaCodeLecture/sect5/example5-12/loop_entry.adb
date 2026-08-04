pragma SPARK_Mode (On);
package body Loop_Entry is

   procedure Test (A,B: in out Integer) is
      Aold : constant Integer := A;
      Bold : constant Integer := B;
   begin
      -- pragma Assert (A = Aold and B  = Bold);
      while (A > 0) loop
         A := A - 1;
         B := B + 1;
         pragma Loop_Invariant (A + B = Aold + Bold);
      end loop;
   end Test;

end Loop_Entry;
