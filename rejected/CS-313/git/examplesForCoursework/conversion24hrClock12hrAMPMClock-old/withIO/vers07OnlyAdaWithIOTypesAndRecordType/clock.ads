pragma SPARK_Mode;


package Clock is
   
   type Hour is new Integer range 0 .. 23;
   
   type Hour12 is new Integer range 0 .. 11;
   
   type Ampm is (Am,Pm);
   
   type Hours_Ampm is 
      record
	 Hours   : Hour12;
	 Mode    : Ampm;
      end record;
   
   -- See ../README.txt about that this is not really the exact conversion
   -- the example is kept as it is so that the reader can concentrate on 
   -- understanding a simple conditional.
   
   
   function To12 (H : Hour) return Hours_Ampm;
     
   procedure To12Proc(H : in Hour; O : out Hours_Ampm); 
     
end Clock;
     
     
   
     
   
