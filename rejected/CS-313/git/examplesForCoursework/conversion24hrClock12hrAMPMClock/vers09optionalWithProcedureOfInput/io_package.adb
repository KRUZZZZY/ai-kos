pragma SPARK_Mode (On);	
       		  
with AS_IO_Wrapper;  use AS_IO_Wrapper; 		  

package body Io_Package  is				  
	     
   procedure Get_Hour(H : out Hour) is		
      T  : Integer;
   begin     
      loop
         AS_Put("Enter a number in hour from 0 .. 23: ");   
         AS_Get(T,"Please type in an integer; please try again");
         exit when T in 0 .. 23;
         AS_Put_Line("Please Enter a number between 0 and 23");
      end loop;		     
      H := T;		     
   end Get_Hour;      	     

   procedure Print_Ampm(Mode : AmPm) is
   begin
      if Mode = Am
      then As_Put("AM");
      else AS_Put("PM");
      end if;
   end Print_Ampm;
  
  
end Io_Package;
