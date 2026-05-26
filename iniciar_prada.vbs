Set oShell = CreateObject("WScript.Shell")
oShell.CurrentDirectory = "C:\Users\WILLIAM\prada-agent"
oShell.Run "python -m streamlit run app.py", 0, False

WScript.Sleep 4000
oShell.Run "http://localhost:8501", 1, False
