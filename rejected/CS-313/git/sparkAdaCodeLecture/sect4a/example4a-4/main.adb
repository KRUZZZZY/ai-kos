pragma SPARK_MODE;
with As_Io_Wrapper; use As_Io_Wrapper;

procedure Main
is  
   Y : Float := 5.0;
begin
   Init;
   while (Y > 0.0) loop
      Y := A1(Y);
      As_Put_Line;
   end loop;
end Main;
   

