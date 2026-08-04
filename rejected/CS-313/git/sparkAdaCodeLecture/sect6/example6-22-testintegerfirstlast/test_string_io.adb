pragma SPARK_Mode (On);

with AS_Io_Wrapper;  use AS_Io_Wrapper; 


procedure Test_String_IO is
   Length_String : constant Integer := 512;
   -- strings as variables must have fixed length in SPARK Ada 
   -- the length we have chosen in this example is determined here by this value
   -- which is a constant.
   
   X : String(1 .. Length_String);
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
   -- the next two lines initialize standard_output and _input
   AS_Init_Standard_Output;
   AS_Init_Standard_Input;   
   -- the next line will prompt for a string and then enter in X and Z 
   -- the string put it will be written into X, and Z determines how long the string input was
   -- The part of X which is longer than Z will stay as it was before, and this X is uninitialised
   -- it will be a random stringx

   AS_Put_Line("Type in some string");
   AS_Get_Line(X,Z);
   -- The string which was entered are the first Z letters of X (the rest is as it was
   --    before the procedure was executed)
   -- we make sure that Z is <= the length of the strings we have to avoid out of range errors.
   if Z > Length_String then Z := Length_String; end if;
   pragma Assert (Z <= Length_String);
   -- Print out the string typed in by the user.
   AS_Put("You typed in '");
   AS_Put(X(1 .. Z));
   -- X(1 .. Z) is since z is of type string 
   --             the substring of length Z of X.
   AS_Put("'");
end Test_String_IO;     
   

