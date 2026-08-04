pragma SPARK_Mode;

procedure Main (N : in Integer; I,Res : out Integer) is
begin     
   I := 0; 	     
   Res := 0;
   loop
      pragma Loop_Invariant (Res = 2 * I and Res < N);
      I := I + 1;	       
      Res := Res + 2; 
      exit when Res >= N;
   end loop;
end Main;

      


