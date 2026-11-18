@echo off
setlocal
set "ROOT=%~dp0"
if exist "%ROOT%.venv\Lib\site-packages" (
  if defined PYTHONPATH (
    set "PYTHONPATH=%ROOT%;%ROOT%.venv\Lib\site-packages;%PYTHONPATH%"
  ) else (
    set "PYTHONPATH=%ROOT%;%ROOT%.venv\Lib\site-packages"
  )
) else (
  if defined PYTHONPATH (
    set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
  ) else (
    set "PYTHONPATH=%ROOT%"
  )
)
python "%ROOT%sana" %*
exit /b %ERRORLEVEL%
