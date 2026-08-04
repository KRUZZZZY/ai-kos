This example contains a very simple loop example.

vers1OnlyAdaNoMainAdbFile
      contains the Ada files without a main.adb file

vers2OnlyAdaWithMainAdbFile
      contains in addition to vers1OnlyAdaNoMainAdbFile 
      a main.adb file

vers3DataInformationFlowAnalyss
      contains in addition to vers2OnlyAdaWithMainAdbFile
      the depends clauses so that it passes the data and information flow
      analysis

vers4VerificationConditionsNoOverflowCheck
      contains in addition to vers4VerificationConditionsNoOverflowCheck
      simple verification conditions.
      It doesn't pass the range condition if started from main.gpr
      If you run it start it with mainWithoutRangeCheck.gpr
         everything is passed because no range conditions are checked
      
vers5FullVersion
      extends vers4VerificationConditionsNoOverflowCheck so that it
      passes the verificaiton conditions
      is to be run starting with main.gpr
