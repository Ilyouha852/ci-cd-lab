
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Docker connectivity check') {
            steps {
                bat '''
                    whoami
                    where docker
                    docker --version
                    docker compose version
                    docker info
                '''
            }
        }

        stage('Install dependencies') {
            steps {
                bat 'python -m pip install --upgrade pip'
                bat 'python -m pip install -r requirements.txt'
            }
        }

        stage('Run tests') {
            steps {
                bat 'python -m pytest tests -v'
            }
        }

        stage('Build') {
            steps {
                bat 'python -m py_compile app.py database.py config.py'
            }
        }

        stage('Deploy application') {
            steps {
                powershell '''
                    $ErrorActionPreference = "Stop"

                    $appPath = Join-Path $env:WORKSPACE "app.py"
                    $logDir = Join-Path $env:WORKSPACE "logs"
                    $stdoutLog = Join-Path $logDir "app.log"
                    $stderrLog = Join-Path $logDir "app-error.log"

                    New-Item -ItemType Directory -Force `
                        -Path $logDir | Out-Null

                    # Находим предыдущий экземпляр приложения
                    $oldProcesses = Get-CimInstance Win32_Process |
                        Where-Object {
                            $_.Name -match '^python(w)?\\.exe$' -and
                            $_.CommandLine -and
                            $_.CommandLine.IndexOf(
                                $appPath,
                                [StringComparison]::OrdinalIgnoreCase
                            ) -ge 0
                        }

                    foreach ($item in $oldProcesses) {
                        Stop-Process -Id $item.ProcessId -Force
                    }

                    Start-Sleep -Seconds 2

                    # Определяем интерпретатор Python
                    $python = (Get-Command python.exe).Source

                    # Запускаем Flask в отдельном процессе
                    $process = Start-Process `
                        -FilePath $python `
                        -ArgumentList @("-u", "app.py") `
                        -WorkingDirectory $env:WORKSPACE `
                        -RedirectStandardOutput $stdoutLog `
                        -RedirectStandardError $stderrLog `
                        -PassThru

                    # Ждём готовности веб-сервера
                    $ready = $false

                    for ($i = 0; $i -lt 20; $i++) {
                        Start-Sleep -Seconds 1

                        $process.Refresh()

                        if ($process.HasExited) {
                            break
                        }

                        try {
                            $response = Invoke-WebRequest `
                                -Uri "http://127.0.0.1:5000/" `
                                -TimeoutSec 2 `
                                -UseBasicParsing

                            if ($response.StatusCode -eq 200) {
                                $ready = $true
                                break
                            }
                        }
                        catch {
                            # Сервер ещё запускается
                        }
                    }

                    if (-not $ready) {
                        if ($process.HasExited) {
                            Write-Host "Application error log:"
                            if (Test-Path $stderrLog) {
                                Get-Content $stderrLog
                            }
                        }

                        throw "Flask application did not become ready on port 5000"
                    }

                    Write-Host "Application is running."
                    Write-Host "PID: $($process.Id)"
                    Write-Host "URL: http://127.0.0.1:5000/"
                '''
            }
        }
    }

    post {
        success {
            echo 'Сборка завершена. Веб-приложение продолжает работать.'
        }
        failure {
            echo 'Ошибка сборки или запуска приложения. Проверьте логи.'
        }
    }
}
