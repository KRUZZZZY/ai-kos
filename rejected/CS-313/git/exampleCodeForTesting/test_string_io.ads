-- this example asks on command line for a string terminated by a line break.
-- then it prints out that string

pragma SPARK_Mode (On);

with SPARK.Text_IO;
use  SPARK.Text_IO;



procedure Test_String_IO
  with Global => (Output => (Standard_Output, Standard_Input));
