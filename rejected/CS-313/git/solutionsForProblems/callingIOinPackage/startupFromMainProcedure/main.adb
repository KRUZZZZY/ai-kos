pragma SPARK_Mode (On);
       
with examplepackage; use examplepackage;		
with AS_IO_Wrapper;  use AS_IO_Wrapper; 
    			
procedure Main
is
begin
   AS_Init_Standard_Input; 
   AS_Init_Standard_Output;
   example;	
end Main;      					

