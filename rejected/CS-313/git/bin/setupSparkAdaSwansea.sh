#!/bin/bash

shareDir=~/.local/share


# create a directory bin for binary files
echo mkdir -p $HOME/bin
mkdir -p $HOME/bin


echo mkdir -p $HOME/git
mkdir -p $HOME/git

if [ -d $HOME/git/criticalhighintegritysystems/ ]; then
    echo cd $HOME/git/criticalhighintegritysystems/; echo git pull
    cd $HOME/git/criticalhighintegritysystems/; git pull
else
    echo cd $HOME/git/; git clone https://anton_setzer@bitbucket.org/anton_setzer/criticalhighintegritysystems.git    
    cd $HOME/git/; git clone https://anton_setzer@bitbucket.org/anton_setzer/criticalhighintegritysystems.git    
fi

# add xml files defining mime types gpr and mlw to ~/.local/share/mime/packages/
echo cp $HOME/git/criticalhighintegritysystems/lib/application-gpr.xml $shareDir/mime/packages/
cp $HOME/git/criticalhighintegritysystems/lib/application-gpr.xml $shareDir/mime/packages/

echo cp $HOME/git/criticalhighintegritysystems/lib/application-mlw.xml $shareDir/mime/packages/
cp $HOME/git/criticalhighintegritysystems/lib/application-mlw.xml $shareDir/mime/packages/


# add desktop entries for why3 and gps to ~/.local/share/applications/

echo cp $HOME/git/criticalhighintegritysystems/lib/callwhy3.desktop $shareDir/applications/
cp $HOME/git/criticalhighintegritysystems/lib/callwhy3.desktop $shareDir/applications/

echo cp $HOME/git/criticalhighintegritysystems/lib/callgps.desktop $shareDir/applications/
cp $HOME/git/criticalhighintegritysystems/lib/callgps.desktop $shareDir/applications/


# add the scripts callgps and callmlw to the user's bin directory

echo cp $HOME/git/criticalhighintegritysystems/bin/callgps $HOME/bin
cp $HOME/git/criticalhighintegritysystems/bin/callgps $HOME/bin

echo cp $HOME/git/criticalhighintegritysystems/bin/callwhy3 $HOME/bin
cp $HOME/git/criticalhighintegritysystems/bin/callwhy3 $HOME/bin


echo cp $HOME/git/criticalhighintegritysystems/bin/mygnatprove $HOME/bin
cp $HOME/git/criticalhighintegritysystems/bin/mygnatprove $HOME/bin

echo cp $HOME/git/criticalhighintegritysystems/bin/updateGitCritsys $HOME/bin
cp $HOME/git/criticalhighintegritysystems/bin/updateGitCritsys $HOME/bin

echo cp $HOME/git/criticalhighintegritysystems/bin/createGitRepository.sh $HOME/bin
cp $HOME/git/criticalhighintegritysystems/bin/createGitRepository.sh $HOME/bin


echo chmod u+x $HOME/bin/callgps
chmod u+x $HOME/bin/callgps

echo chmod u+x $HOME/bin/callwhy3
chmod u+x $HOME/bin/callwhy3

echo chmod u+x $HOME/bin/mygnatprove
chmod u+x $HOME/bin/mygnatprove

echo chmod u+x $HOME/bin/createGitRepository.sh
chmod u+x $HOME/bin/createGitRepository.sh

echo "The following instructions will change your file settings so that"
echo "when clicking on selected spark ada and why3 files the"
echo "corresponding applications are run"
echo " "
echo "This will override any file associations you have done before"
echo "If you want to keep them as they are you need to do it manually"
echo " by associating "
echo "    .gpr files with command callgps and "
echo "    .mlw files with command callwhy3 "
echo " and you need to answer no in the following"
echo "Othewise answer yes"


echo "Change file associations (yes/no)"
read userinput
if [ ! "$userinput" = "yes" ];
 then
     echo "*** File associations were NOT changed ***"
else
    # backup ~/.local/share/applications/mimeapps.list  
    # since it might contain already some user defined mime types

    echo mv $shareDir/applications/mimeapps.list $shareDir/applications/mimeapps.list.old

    mv $shareDir/applications/mimeapps.list $shareDir/applications/mimeapps.list.old

    # overwrite the file 
    # ~/.local/share/applications/mimeapps.list  
    # by making associations for .gpr and .mlw


    echo cp $HOME/git/criticalhighintegritysystems/lib/mimeapps.list $shareDir/applications/
    cp $HOME/git/criticalhighintegritysystems/lib/mimeapps.list $shareDir/applications/

    # update mime database

    update-mime-database ~/.local/share/mime/

fi

echo "*** If the following command fails then why3 is probably ***"
echo "***   not installed on the machine you are using  *** "
echo "***   Use a different machine  *** "

if [ -x /usr/bin/why3 ];
then why3 config --detect-provers
else /usr/local/opam/system/bin/why3 config --detect-provers
fi 

