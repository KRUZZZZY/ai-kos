pragma SPARK_Mode (On);

with AS_IO_Wrapper;  use AS_IO_Wrapper; 

package body Print_Package  is

  procedure Print_Ampm(Mode : in AmPm) is
  begin
     if Mode = Am
     then As_Put("AM");
     else AS_Put("PM");
     end if;
  end Print_Ampm;
  
  
end Print_Package;
