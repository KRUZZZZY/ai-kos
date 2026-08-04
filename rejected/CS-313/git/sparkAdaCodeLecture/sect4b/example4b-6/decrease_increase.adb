pragma SPARK_Mode;

procedure Decrease_Increase(X,Y : in out Integer; Z : in Integer) is
begin
   loop
      exit when Z < 0 or X <= 0;
      -- overflow error reported
      -- see README.txt
      X := X - 1; Y := Y + 1;
   end loop;
end Decrease_Increase;

