@echo off
REM Executa o Farmer Dashboard automaticamente
REM Usado pelo Agendador de Tarefas do Windows

cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo [%date% %time%] Iniciando Farmer Dashboard... >> executar.log
python main.py >> executar.log 2>&1
echo [%date% %time%] Concluido. >> executar.log
