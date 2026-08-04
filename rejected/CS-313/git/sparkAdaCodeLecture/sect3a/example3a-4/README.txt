gnatmake example6

gnatprove -P main.gpr --proof=progressive
reports
that Mon, Tue, ..  are not referenced.
Seems to be overly strict, so error can be ignored

Furthermore
warning: no bodies have been analyzed by GNATprove

reason: spark_mode is not set to on
