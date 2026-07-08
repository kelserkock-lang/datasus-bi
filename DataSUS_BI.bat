@echo off
title DataSUS BI Pro - Iniciando...
color 1F
cls

echo.
echo  ============================================
echo    DataSUS BI Pro - Painel de Saude Publica
echo  ============================================
echo.

:: Navegar para a pasta do script
cd /d "%~dp0"

:: Definir caminhos do Python (usa o do sistema se nao encontrar)
set "PYTHON_PATH=C:\Users\kelse\AppData\Local\Programs\Python\Python313\python.exe"
set "STREAMLIT_PATH=C:\Users\kelse\AppData\Local\Programs\Python\Python313\Scripts\streamlit.exe"

:: Verificar se Streamlit existe
if not exist "%STREAMLIT_PATH%" (
    echo  [ERRO] Streamlit nao encontrado em:
    echo  %STREAMLIT_PATH%
    echo.
    echo  Tentando usar 'streamlit' do PATH...
    set "STREAMLIT_PATH=streamlit"
)

:: Verificar se app.py existe
if not exist "app.py" (
    echo  [ERRO] Arquivo app.py nao encontrado!
    echo  Pasta atual: %CD%
    pause
    exit /b 1
)

echo  [1/3] Iniciando servidor Streamlit...
echo.

:: Matar processos streamlit anteriores na porta 8501 (opcional)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8501" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Iniciar Streamlit em segundo plano
start /B "" "%STREAMLIT_PATH%" run app.py --server.headless true --server.port 8501 --server.address localhost

echo  [2/3] Aguardando servidor ficar pronto...

:: Aguardar ate 30 segundos pelo servidor
set /a TENTATIVAS=0
:AGUARDAR
set /a TENTATIVAS+=1
if %TENTATIVAS% gtr 30 (
    echo.
    echo  [ERRO] Servidor nao iniciou em 30 segundos.
    echo  Verifique se ha erros no terminal.
    pause
    exit /b 1
)

:: Verificar se a porta 8501 esta escutando
netstat -an | findstr ":8501" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    ping -n 2 127.0.0.1 >nul
    goto AGUARDAR
)

echo  [3/3] Servidor pronto! Abrindo navegador...
echo.

:: Pequena pausa extra para garantir que o app carregou
ping -n 2 127.0.0.1 >nul

:: Abrir navegador
start "" "http://localhost:8501"

echo  ============================================
echo    App rodando em: http://localhost:8501
echo.
echo    NAO FECHE esta janela enquanto usar o app.
echo    Para encerrar: feche esta janela ou Ctrl+C
echo  ============================================
echo.

:: Manter janela aberta (streamlit roda em background)
:LOOP
ping -n 5 127.0.0.1 >nul
:: Verificar se streamlit ainda esta rodando
netstat -an | findstr ":8501" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [AVISO] Servidor parou. Pressione qualquer tecla para sair.
    pause >nul
    exit /b 0
)
goto LOOP
