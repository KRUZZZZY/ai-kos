--pragma SPARK_Mode (Off);

package body junction is
   -- Define initial states of segments to 
   -- indicate positions of cars.

 
  
   function F(U: in out SmInteger) return SmInteger is
   begin
      if U < 1000 then
         U := U + 1;
      end if;
      
      return U;
      
   end F;
 
   function G(U: in out SmInteger) return SmInteger is
   begin
      if U < 1000 then
         U := U + 2; 
      end if;
      
      return U;
      
   end G;

   procedure sideEffect(Y: in out SmInteger; X: out SmInteger) is  
   begin
      X := F(Y) + G(Y);

   end sideEffect;
   
end junction;
