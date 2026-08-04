Pragma SPARK_Mode;	
       	
package body Example_Side_Effects is 	
		
   function Increment_And_Return (X : in out Integer) return Integer is
   begin	 
      X := X + 1;	
      Return X + 1;
   end Increment_And_Return;
  
end Example_Side_Effects; 	  
