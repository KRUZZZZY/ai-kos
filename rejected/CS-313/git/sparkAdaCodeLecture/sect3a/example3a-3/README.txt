compiles correctly

gnatprove -P main.gpr --proof=progressive
reports

example5.adb:7:37: warning: literal "Sat" is not referenced [-gnatwu]
example5.adb:7:41: warning: literal "Sun" is not referenced [-gnatwu]
warning: no bodies have been analyzed by GNATprove

the last warning is because SPARK_Mode is not on;

The warnings seems to be overly strict because there is no need to always
 reference all days
