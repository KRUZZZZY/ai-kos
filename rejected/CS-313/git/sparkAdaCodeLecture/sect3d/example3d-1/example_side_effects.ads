Pragma SPARK_Mode;	
       	
package Example_Side_Effects is	
		
function Increment_And_Return (X : in out Integer) return Integer
  with Side_Effects;
  
end Example_Side_Effects; 	  
