!macro customInstall
  nsExec::ExecToLog 'netsh advfirewall firewall delete rule name="ERGoSIGHT Backend"'
  nsExec::ExecToLog 'netsh advfirewall firewall add rule name="ERGoSIGHT Backend" dir=in action=allow program="$INSTDIR\resources\backend\ergosight-backend.exe" protocol=TCP localport=8000 profile=private'
!macroend

!macro customUnInstall
  nsExec::ExecToLog 'netsh advfirewall firewall delete rule name="ERGoSIGHT Backend"'
!macroend
