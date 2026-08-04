pragma SPARK_Mode (On);

with AS_IO_Wrapper;  use AS_IO_Wrapper; 


procedure Main is
begin
   -- First test of  Integer input/output
   --
   
   
   -- First we initialise standard_input and standard output
   AS_Init_Standard_Output;
   AS_Init_Standard_Input;   
   AS_Put("Integer'First = ");   
   AS_Put_Line(Integer'First);
   AS_Put("Integer'Last = ");   
   AS_Put_Line(Integer'Last);
   
end Main;
   

