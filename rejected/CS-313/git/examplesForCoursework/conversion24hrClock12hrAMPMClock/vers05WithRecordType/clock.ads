pragma SPARK_Mode;


package Clock is
   
   subtype Hour is Integer range 0 .. 23;
   
   subtype Hour12 is Integer range 0 .. 11;
   
   type Ampm is (Am,Pm);
   
   type Hours_Ampm is 
      record
         Hours   : Hour12;
         Mode    : Ampm;
      end record;
   
   -- See ../README.txt about that this is not really the exact conversion
   -- the example is kept as it is so that the reader can concentrate on 
   -- understanding a simple conditional.
   
   
   procedure To12Proc(H : in Hour; O : out Hours_Ampm); 
     
end Clock;
     
     

     
   
