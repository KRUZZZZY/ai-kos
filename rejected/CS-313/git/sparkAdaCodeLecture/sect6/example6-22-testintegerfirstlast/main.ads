-- This is an example of interation with console input
-- It can be compiled using gnatmake (or from gps)
-- when executed it asks for
-- an integer to be entered on console.
-- if the value entered was an integer, it prints it out and stops 
-- otherwise it asks again fo an integer


pragma SPARK_Mode (On);

with SPARK.Text_IO;
use  SPARK.Text_IO;


procedure Main
  with Global => (Output => (Standard_Output, Standard_Input));
