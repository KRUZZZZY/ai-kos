pragma SPARK_Mode (On);

with AS_IO_Wrapper;  use AS_IO_Wrapper; 


procedure Main is
   X : Integer;
   Length_String : constant Integer := 512;
   -- strings as variables must have fixed length in SPARK Ada 
   -- the length we have chosen in this example is determined here by this value
   -- which is a constant.
   
   Y : String(1 .. Length_String);
   -- strings as variables must have fixed length
   -- X will store the input by the user.
   
   Z : Natural;
   -- will be the length of the string input.
   -- so the actual input will be the first Z characters of X
   -- which in SPARK Ada is written as
   -- X ( 1 .. Z);
   --
   -- In general for a string X, X (i .. j) is the substring starting at the ith character
   -- and ending at the jth character.

begin
   -- First test of  Integer input/output
   --
   
   
   -- First we initialise standard_input and standard output
   AS_Init_Standard_Output;
   AS_Init_Standard_Input;   
   AS_Put_Line("Begin of Test of Integer I/O ");   

   -- Print on screen "Type in some number"
   AS_Put_Line("Type in some number");
   -- ask for an  integer (in variable X) until an integer has been entered
   --   if something else has been entered ask again
   AS_Get(X,"Please type in an integer; please try again");
   -- Print out the resultx
   AS_Put_Line("You typed in");
   AS_Put_Line(X);
   AS_Put_Line("End of Test of Integer I/O ");
   
   -- Secondly test of string I/O
   --
   
   
   AS_Put_Line("Begin of Test of String I/O ");      
   -- the next two lines initialize standard_output and _input
   -- the next line will prompt for a string and then enter in Y and Z 
   -- the string put it will be written into Y, and Z determines how long the string input was
   -- The part of Y which is longer than Z will stay as it was before, and this Y is uninitialised
   -- it will be a random stringx

   AS_Put_Line("Type in some string");
   AS_Get_Line(Y,Z);
   -- The string which was entered are the first Z letters of Y (the rest is as it was
   --    before the procedure was executed)
   -- we make sure that Z is <= the length of the strings we have to avoid out of range errors.
   if Z > Length_String then Z := Length_String; end if;
   pragma Assert (Z <= Length_String);
   -- Print out the string typed in by the user.
   AS_Put("You typed in '");
   AS_Put(Y(1 .. Z));
   -- Y(1 .. Z) is since z is of type string 
   --             the substring of length Z of Y.
   AS_Put_Line("'");
   AS_Put_Line("End of Test of String I/O ");      
   
end Main;
   

