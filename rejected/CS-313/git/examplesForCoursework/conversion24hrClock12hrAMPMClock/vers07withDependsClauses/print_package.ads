pragma SPARK_Mode (On);
       
with SPARK.Text_IO;
use SPARK.Text_IO;
with Clock;  use Clock; 

package Print_Package is

   procedure Print_Ampm(Mode : in AmPm) with	
     Global => (In_Out => Standard_Output),
     Depends => (Standard_Output  => (Mode,Standard_Output));
   
end Print_Package;
