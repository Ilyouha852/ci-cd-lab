pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Docker connectivity check') {
            steps {
                bat '''
                    docker info
                    docker compose version
                '''
            }
        }

        stage('Install dependencies') {
            steps {
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
                bat 'docker compose config'
            }
        }

        stage('Build Docker image') {
            steps {
                bat 'docker compose -p caraccounting build'
            }
        }

        stage('Deploy with Docker Compose') {
            steps {
                powershell '''
                    $ErrorActionPreference = "Stop"
                    Set-Location $env:WORKSPACE

                    Write-Host "Starting application and Nginx..."

                    docker compose -p caraccounting up -d --build
                    if ($LASTEXITCODE -ne 0) {
                        throw "Docker Compose deployment failed"
                    }

                    Write-Host "Waiting for the website..."

                    $ready = $false

                    for ($i = 0; $i -lt 30; $i++) {
                        Start-Sleep -Seconds 2

                        try {
                            $response = Invoke-WebRequest `
                                -Uri "http://localhost/" `
                                -TimeoutSec 3 `
                                -UseBasicParsing

                            if ($response.StatusCode -eq 200) {
                                $ready = $true
                                break
                            }
                        }
                        catch {
                            Write-Host "Website is not ready yet..."
                        }
                    }

                    if (-not $ready) {
                        docker compose -p caraccounting ps
                        docker compose -p caraccounting logs --tail=100
                        throw "Website did not become available at http://localhost/"
                    }

                    docker compose -p caraccounting ps

                    Write-Host "Deployment successful."
                    Write-Host "Website: http://localhost/"
                '''
            }
        }
    }

    post {
        success {
            echo 'CI/CD завершён успешно. Приложение запущено в Docker.'
            echo 'Сайт доступен по адресу http://localhost/'
        }

        failure {
            echo 'Ошибка CI/CD. Проверьте логи этапа, завершившегося с ошибкой.'
        }
    }
}
