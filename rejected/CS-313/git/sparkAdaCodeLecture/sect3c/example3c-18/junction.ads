--pragma SPARK_Mode (Off);

package junction is
  

   type SmInteger is new Integer range 1 .. 1000;
   procedure sideEffect(
                        Y: in out SmInteger; X: out SmInteger);
		
end junction;
