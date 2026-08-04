gnatprove -P main.gpr --proof=progressive
 succeeds with no problem
gnatmake test_string_io.adb
gnatmake test_integer_io.adb 
 both succeed with no problem

Explanation
~~~~~~~~~~~~
This file contains a wrapper class for IO
as_io_wrapper.ads and
as_io_wrapper.adb

which makes use of spark ada files
spark.ads
spark-text_io.ads
spark-text_io.adb
spark-text_io-integer_io.ads
spark-text_io-integer_io.adb

which are adaptions from files obtained as part of the distribution located at
/opt/spark2014/share/examples/spark/spark_io/
or
/usr/gnat/share/examples/spark/spark_io/

It contains two very simple examples for using it:

test_integer_io.adb
test_string_io.adb


The lines 
pragma SPARK_Mode (On);
and
with Global => (Output => (Standard_Output, Standard_Input));

are added so that the code is compatible with Spark_Ada.

To try it out you can
- click on main.gpr to activate gnatstudio
- open from there the file test_integer_io.adb   or test_string_io.adb
- execute Build -> Project -> Build <current file>
  this should compile the code
- now you can execute it using 
  Build -> Run 
   and replacing the command used (using preferences ) by xterm -hold 
  execute from terminal
   ./test_integer_io
   ./test_string_io



