@echo off
title DataSUS BI - Assistente CLI
color 1F
cls

echo.
echo  ============================================
echo    DataSUS BI - Assistente de linha de comando
echo  ============================================
echo.

:: Navegar para a pasta do script
cd /d "%~dp0"

:: Escolher o Python: preferencia para a venv do projeto
set "PYTHON_PATH=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_PATH%" (
    echo  [aviso] venv nao encontrada em .venv\Scripts\
    echo          usando o Python do sistema...
    set "PYTHON_PATH=C:\Users\kelse\AppData\Local\Programs\Python\Python313\python.exe"
)

:: Ultimo recurso: o python do PATH
if not exist "%PYTHON_PATH%" (
    if "%PYTHON_PATH%" neq "python" (
        echo  [aviso] Python nao encontrado no caminho padrao, tentando 'python' do PATH...
        set "PYTHON_PATH=python"
    )
)

:: Verificar se o script existe
if not exist "datasus_cli.py" (
    echo  [ERRO] Arquivo datasus_cli.py nao encontrado!
    echo  Pasta atual: %CD%
    pause
    exit /b 1
)

:: Rodar o assistente, repassando qualquer argumento
"%PYTHON_PATH%" datasus_cli.py %*

echo.
echo  ============================================
echo    Sessao encerrada.
echo  ============================================
pause
