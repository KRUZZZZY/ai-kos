gnatmake example7.adb
  succeeds without problems

gnatprove -P main.gpr --proof=progressive
reports 
warning: no bodies have been analyzed by GNATprove
because 
  pragma SPARK_MODE; 
not used
