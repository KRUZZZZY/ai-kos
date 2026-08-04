pragma SPARK_Mode (On);
       
with SPARK.Text_IO;
use SPARK.Text_IO;
with Clock;  use Clock; 

package Io_Package is	
		   
   procedure Get_Hour(H : out Hour) with			
     Global => (In_Out => (Standard_Input,Standard_Output)),   	
     Depends => (H => Standard_Input,				
                 Standard_Input => (Standard_Input),		
                 Standard_Output => (Standard_Input, Standard_Output));

   procedure Print_Ampm(Mode : in AmPm) with	
     Global => (In_Out => Standard_Output),
     Depends => (Standard_Output  => (Mode,Standard_Output));
   
end Io_Package;
