pragma SPARK_Mode;

package Clock is
   
   type Months is (Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec);
   subtype Month_Days is Integer range 1 .. 31; 
   subtype Year_Days  is Integer range 1 .. 365;
   subtype Max_Days_Before is Integer range 0 .. 334;
   
   type Date is record
      M : Months;
      D : Month_Days;
   end record;
  
     
   Days_Before : constant array (Months) of Max_Days_Before :=
     (Jan => 0,
      Feb => 31,
      Mar => 59,
      Apr => 90,
      May => 120,
      Jun => 151,
      Jul => 181,
      Aug => 212,
      Sep => 243,
      Oct => 273,
      Nov => 304,
      Dec => 334); --Days before the first of the corresponding month
   
   Max_Days : constant array (Months) of Month_Days :=
     (Jan => 31,
      Feb => 28,
      Mar => 31,
      Apr => 30,
      May => 31,
      Jun => 30,
      Jul => 31,
      Aug => 31,
      Sep => 30,
      Oct => 31,
      Nov => 30,
      Dec => 31);

   function Valid_Input (Dt: Date) return Boolean
     with 
       Depends => (Valid_Input'Result => Dt),
       Post => Valid_Input'Result = (Dt.D <= Max_Days (Dt.M));
   
   function Days_Before_Month (M : Months) return Max_Days_Before
     with
       Depends => (Days_Before_Month'Result => M),
         Post => Days_Before_Month'Result = Days_Before (M);
     
   function Accumulated_Days (Dt : Date) return Year_Days
     with
       Pre => Valid_Input (Dt),
       Depends => (Accumulated_Days'Result => Dt),
       Post => Accumulated_Days'Result = Year_Days (Days_Before(Dt.M) +Dt.D);
    
   procedure Accumulated_Days_Proc(Dt : in Date; Y : out Year_Days)
     with 
       Pre => Valid_Input(Dt),
       Depends => (Y => Dt),
       Post => Y = Year_Days (Days_Before (Dt.M) +Dt.D); 

   --Changing 3 letters to full month name
   function Month_To_String (M : Months) return String
     with Depends => (Month_To_String'Result => M);
   
   procedure String_To_Month (
      Abbrev  : String;
      Success : out Boolean;
      M       : out Months
   )
     with Depends => ((Success, M) => Abbrev);
  
end Clock;

