gnatmake example5.adb
 succeeds

gnatprove -P main.gpr --proof=progressive
reports
warning: no bodies have been analyzed by GNATprove

because SPARK_Mode is not set to on
