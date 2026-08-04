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


