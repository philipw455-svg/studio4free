@echo off
rem Builds Studio4Free.exe with the C# compiler that ships with Windows. Needs Python with Pillow for the icon.
cd /d "%~dp0"
python -c "from PIL import Image; Image.open('../assets/brand/mark.png').save('Studio4Free.ico', sizes=[(16,16),(32,32),(48,48),(256,256)])" || exit /b 1
"%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe /win32icon:Studio4Free.ico /out:Studio4Free.exe Studio4Free.cs
