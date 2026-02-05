' Video Downloader - Windowless Launcher
' Runs without console window

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get script directory
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Build command
pythonw = scriptDir & "\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(pythonw) Then
    MsgBox "Virtual environment not found. Please run setup.bat first.", vbCritical, "Video Downloader"
    WScript.Quit 1
End If

' Run without window
WshShell.CurrentDirectory = scriptDir
WshShell.Run """" & pythonw & """ -m video_downloader", 0, False
