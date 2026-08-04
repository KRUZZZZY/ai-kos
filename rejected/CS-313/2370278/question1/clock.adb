pragma SPARK_Mode;


package body Clock is

   function Days_Before_Month (M : Months) return Max_Days_Before is
   begin
      if M = Jan then
         return 0;
      elsif M = Feb then
         return Max_Days(Jan);
      elsif M = Mar then
         return Max_Days(Jan)+Max_Days(Feb);
      elsif M = Apr then
         return Max_Days(Jan)+Max_Days(Feb)+Max_Days(Mar);     
      elsif M = May then
         return Max_Days(Jan)+Max_Days(Feb)+Max_Days(Mar)+Max_Days(Apr);
      elsif M = Jun then
         return Max_Days(Jan)+Max_Days(Feb)+Max_Days(Mar)+Max_Days(Apr)
         +Max_Days(May);
      elsif M = Jul then
         return Max_Days(Jan)+Max_Days(Feb)+Max_Days(Mar)+Max_Days(Apr)
         +Max_Days(May)+Max_Days(Jun);   
      elsif M = Aug then
         return Max_Days(Jan)+Max_Days(Feb)+Max_Days(Mar)+Max_Days(Apr)
         +Max_Days(May)+Max_Days(Jun)+Max_Days(Jul);   
      elsif M = Sep then
         return Max_Days(Jan)+Max_Days(Feb)+Max_Days(Mar)+Max_Days(Apr)
         +Max_Days(May)+Max_Days(Jun)+Max_Days(Jul)+Max_Days(Aug);   
      elsif M = Oct then
         return Max_Days(Jan)+Max_Days(Feb)+Max_Days(Mar)+Max_Days(Apr)
           +Max_Days(May)+Max_Days(Jun)+Max_Days(Jul)+Max_Days(Aug)
         +Max_Days(Sep);   
      elsif M = Nov then
         return Max_Days(Jan)+Max_Days(Feb)+Max_Days(Mar)+Max_Days(Apr)
           +Max_Days(May)+Max_Days(Jun)+Max_Days(Jul)+Max_Days(Aug)
         +Max_Days(Sep)+Max_Days(Oct);   
      else
         return Max_Days(Jan)+Max_Days(Feb)+Max_Days(Mar)+Max_Days(Apr)
           +Max_Days(May)+Max_Days(Jun)+Max_Days(Jul)+Max_Days(Aug)
         +Max_Days(Sep)+Max_Days(Oct)+Max_Days(Nov);   
      end if;
   end Days_Before_Month;
  
   function Accumulated_Days (Dt : Date) return Year_Days is
     (Year_Days (Days_Before (Dt.M) +Dt.D));
   
  procedure Accumulated_Days_Proc (Dt : in Date; Y : out Year_Days) is
  begin
      Y:=Accumulated_Days(Dt);
  end Accumulated_Days_Proc;
   
  function Month_To_String (M : Months) return String is
   begin
      case M is
         when Jan => return "January";
         when Feb => return "February";
         when Mar => return "March";
         when Apr => return "April";
         when May => return "May";
         when Jun => return "June";
         when Jul => return "July";
         when Aug => return "August";
         when Sep => return "September";
         when Oct => return "October";
         when Nov => return "November";
         when Dec => return "December";
      end case;
   end Month_To_String;
   
   procedure String_To_Month
     (Abbrev : String;
      Success : out Boolean;
      M : out Months)
   is
   begin
      Success := False;
      M := Jan;
      if Abbrev = "jan" then
         M := Jan;
         Success := True;
      elsif Abbrev = "feb" then
         M := Feb;
         Success := True;
      elsif Abbrev = "mar" then
         M := Mar;
         Success := True;
      elsif Abbrev = "apr" then
         M := Apr;
         Success := True;
      elsif Abbrev = "may" then
         M := May;
         Success := True;
      elsif Abbrev = "jun" then
         M := Jun;
         Success := True;
      elsif Abbrev = "jul" then
         M := Jul;
         Success := True;
      elsif Abbrev = "aug" then
         M := Aug;
         Success := True;
      elsif Abbrev = "sep" then
         M := Sep;
         Success := True;
      elsif Abbrev = "oct" then
         M := Oct;
         Success := True;
      elsif Abbrev = "nov" then
         M := Nov;
         Success := True;
      elsif Abbrev = "dec" then
         M := Dec;
         Success := True;
      end if;
   end String_To_Month;
     
   function Valid_Input (Dt :Date) return Boolean is
   begin
      return Dt.D <= Max_Days(Dt.M);
   end Valid_Input;
end Clock;
     
