mkdir -p ~/.local/share/applications
wget -P ~/.local/share/applications/  https://bitbucket.org/anton_setzer/criticalhighintegritysystems/raw/e4f4dd2228ffdb06fd88ec53ff2b889b653ec64d/setupLinuxLab/gnatstudio.desktop

mkdir -p ~/.local/share/mime/applications/
wget -P ~/.local/share/mime/applications/ https://bitbucket.org/anton_setzer/criticalhighintegritysystems/raw/e4f4dd2228ffdb06fd88ec53ff2b889b653ec64d/setupLinuxLab/x-extension-gpr.xml

xdg-mime install ~/.local/share/mime/applications/x-extension-gpr.xml
update-mime-database ~/.local/share/mime/
