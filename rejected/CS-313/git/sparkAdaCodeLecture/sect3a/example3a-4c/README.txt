gnatmake example5.adb
succeeds

gnatprove -P main.gpr --proof=progressive
returns
warning: no bodies have been analyzed by GNATprove

reason: spark_mode is not set to on
