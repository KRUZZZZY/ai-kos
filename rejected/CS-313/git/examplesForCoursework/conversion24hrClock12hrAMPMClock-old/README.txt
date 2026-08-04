This is an example which can be used as a template for the first question
of the coursework.
 It converts numbers in the range from 0 .. 23 to numbers in the range 0 .. 11
   by subtracting 12 if the number is >= 12.
  Note that this is not a completely in accordance with how the conversion
  from 0 .. 23 hours to hours with am/pm works:
   - to be more realistic
        0 should be become 12
        times t in 1 .. 12 should stay
        times t in 13 .. 23 should become t - 12
   - and there is a special treatment of noon and midnight.
 We keep it as it is so that the example stays easy. 
 We leave it to the reader to adapt this example to a more realistic ones.

There are different versions which correspond to the different stages of 
writing a program similar to the stages in the coursework.

* The full version which uses subtypes instead of types is 
  vers12FullVersionWithIOUsingSubType
* All versions with IO in the name contain a main procedure which when 
    compiled allows to execute the code in a console.
  Otherwise the code can be compiled but needs to be linked from an 
    file to be executed.
* NoLibrary means that Ada's IO is used directly for Input/Output. 
  This can be be compiled but fails checks in SPARKAda
* Using Library means that the code uses a library, which allows to create
  executable files which can be checked using SPARK Ada
  This requires the file  from the asLibraryIO (except for the README.txt file)
  located at
     sparkAdaCodeLecture/asLibraryIO/
  to be added to the directory containing your code (the files are included
  in the examples)
* Versions "WithTypes" mean that integer types for ranges are used
* Versions with "Record type" make use of a record type.
* Versions "without Range" mean that range conditions are not met but
  verification conditions are fulfilled otherwise.
* Version vers12FullVersionWithIOUsingSubType uses instead of types subtypes
  which  is easier to use. 

Note a record occurs only in vers06 and vers07 - the later example refer
  vers08 .. vers11 extend examples in vers04 and vers05
  The reason was that the verification conditions as seen in why3 were
  note well readable when using a record type.
  In the coursework you should use record types for all versions unless
  explicitly stated differently. Especially 2020/21 record types should always
  be used. 

Versions: 
  
withoutIO/vers06OnlyAdaWithTypesAndRecordType
withoutIO/vers08a-DataInformationFlowWithRecordType
withoutIO/vers08DataInformationFlow
withoutIO/vers10FullVersion

withIO/vers03OnlyAdaWithIOIntegersUsingLibrary
withIO/vers04OnlyAdaWithTypes
withIO/vers05OnlyAdaWithIOTypes
withIO/vers07OnlyAdaWithIOTypesAndRecordType
withIO/vers09a-DataInformationFlowWithRecordTypeIO
withIO/vers09b-VerificationConditionsWithoutRange
withIO/vers09DataInformationFlowWithIO
withIO/vers11FullVersionWithIO
withIO/vers12FullVersionWithIOUsingSubType









