[Setup]
AppName=IT Бюджет Медквадрат
AppVersion=1.0.0
DefaultDirName={pf}\ITBudgetMedkvadrat
DefaultGroupName=IT Бюджет Медквадрат
OutputBaseFilename=ITBudgetMedkvadratSetup
SetupIconFile=assets\icon.ico

[Files]
Source="dist\ITBudgetMedkvadrat.exe"; DestDir="{app}"; Flags: ignoreversion
Source="config.yaml"; DestDir="{app}"; Flags: ignoreversion
Source="data\*"; DestDir="{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs
Source="assets\icon.ico"; DestDir="{app}\assets"; Flags: ignoreversion

[Icons]
Name="{group}\ITBudgetMedkvadrat"; Filename="{app}\ITBudgetMedkvadrat.exe"; IconFilename="{app}\assets\icon.ico"
Name="{commondesktop}\ITBudgetMedkvadrat"; Filename="{app}\ITBudgetMedkvadrat.exe"; IconFilename="{app}\assets\icon.ico"