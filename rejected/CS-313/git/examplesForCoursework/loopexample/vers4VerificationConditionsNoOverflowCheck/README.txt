This version extends vers3DataInformationFlowAnalysis by adding 
verification conditions.
This version doesn't pass range checks yet.
It fails SPARK Ada prove all 
     if started from  main.gpr
If you start it from mainWithoutRangeCheck.gpr
     it passes SPARK Ada prove all
     because no range checks will be done

It can be compiled by selecting the main.adb file and choosing
Build -> Project -> Build <current file>
and then  run
using 
Build -> Run -> Custom   
    selecting external terminal
and executing in that terminal
    main  
