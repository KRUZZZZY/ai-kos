pragma SPARK_Mode (On);

with Clock;  use Clock; 

package Print_Package is

   procedure Print_Ampm(Mode : in AmPm);
   
end Print_Package;
