pragma SPARK_MODE;
with As_Io_Wrapper; use As_Io_Wrapper;


procedure main
is  
   Y : Integer := 5;
begin
   Init;
   while (Y > 0) loop
      Y := A1(Y);
      As_Put_Line;
   end loop;
end Main;
   

