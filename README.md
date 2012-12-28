csfd-plex
=========

A plex metadata agent for CSFD (http://csfd.cz)

##Install
To install extract the repository (zip) into the Plugins folder on the plex media server:

* On linux extract to:
/var/lib/plexmediaserver/Library/Application\ Support/Plex\ Media\ Server/Plug-ins/

* On windows extract to:
C:\Documents and Settings\**yourusername**\Local Settings\Application Data\Plex Media Server\Plug-ins\

* On Mac/OSX extract to:
~/Library/Application Support/Plex Media Server/Plug-ins/

##Directory structure
After extraction things should look like,

* On linux:
```
/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/
/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents
/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/DefaultPrefs.json
/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Code
/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Code/__init__.py
/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Resources
/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Resources/icon-default.png
/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Resources/attribution.png
/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Info.plist
```

* On windows

* On Max/OSX:
```
~/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/
~/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents
~/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Code
~/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Code/__init__.py
~/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Code/__init__.pyc
~/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Code/CSFDlookup.py
~/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/DefaultPrefs.json
~/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Info.plist
~/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Resources
~/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Resources/attribution.png
~/Library/Application Support/Plex Media Server/Plug-ins/CSFD.bundle/Contents/Resources/icon-default.png
```