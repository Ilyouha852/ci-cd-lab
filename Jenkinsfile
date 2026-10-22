// Единый pipeline для всех веток.
//   * любая ветка, кроме main: установка зависимостей, тесты, проверка и сборка
//     отдельного CI-образа с уникальным тегом. Деплоя нет, работающее
//     приложение не затрагивается;
//   * ветка main: те же проверки + сборка и деплой через Docker Compose.
//
// Запускать как Multibranch Pipeline (см. README, раздел "Jenkins").

// main определяется и для Multibranch (BRANCH_NAME), и для обычного
// Pipeline from SCM (GIT_BRANCH вида origin/main).
def isMainBranch() {
    def b = env.BRANCH_NAME ?: env.GIT_BRANCH ?: ''
    return b == 'main' || b == 'origin/main' || b == 'refs/heads/main'
}

pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    triggers {
        // Jenkins стоит на localhost, GitHub webhook до него не дотянется,
        // поэтому Jenkins сам раз в пару минут проверяет репозиторий.
        pollSCM('H/2 * * * *')
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
                bat 'docker compose config -q'
            }
        }

        // Не main: образ с уникальным тегом, чтобы не перезаписать образ
        // caraccounting-app, который использует развернутое приложение.
        stage('Build CI Docker image') {
            when {
                not {
                    expression { return isMainBranch() }
                }
            }
            steps {
                script {
                    def branchTag = (env.BRANCH_NAME ?: env.GIT_BRANCH ?: 'manual')
                        .toLowerCase()
                        .replaceAll(/[^a-z0-9_.-]/, '-')

                    env.CI_IMAGE_TAG = "car-accounting-ci:${branchTag}-${env.BUILD_NUMBER}"
                }

                // Docker Hub иногда отвечает TLS handshake timeout, поэтому повторы.
                retry(3) {
                    bat "docker build -t \"${env.CI_IMAGE_TAG}\" ."
                }
            }
        }

        stage('Build Docker image') {
            when {
                expression { return isMainBranch() }
            }
            steps {
                retry(3) {
                    bat 'docker compose -p caraccounting build'
                }
            }
        }

        stage('Deploy with Docker Compose') {
            when {
                expression { return isMainBranch() }
            }

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

        // Публикация образа в Docker Hub: только main и только после успешного
        // деплоя. Нужны credentials типа "Username with password" с ID dockerhub
        // (логин Docker Hub + Access Token). Образ: <логин>/car-accounting.
        stage('Push to Docker Hub') {
            when {
                expression { return isMainBranch() }
            }
            environment {
                DOCKERHUB = credentials('dockerhub')
                IMAGE_REPO = 'car-accounting'
            }
            steps {
                retry(3) {
                    // Без пробела перед "|": иначе пробел попадёт в пароль.
                    // "|| exit /b 1" нужен, чтобы bat падал на любой строке, а не только на последней.
                    bat '''
                        echo %DOCKERHUB_PSW%| docker login -u %DOCKERHUB_USR% --password-stdin || exit /b 1
                        docker build -t %DOCKERHUB_USR%/%IMAGE_REPO%:%BUILD_NUMBER% -t %DOCKERHUB_USR%/%IMAGE_REPO%:latest . || exit /b 1
                        docker push %DOCKERHUB_USR%/%IMAGE_REPO%:%BUILD_NUMBER% || exit /b 1
                        docker push %DOCKERHUB_USR%/%IMAGE_REPO%:latest || exit /b 1
                    '''
                }
            }
            post {
                always {
                    bat(returnStatus: true, script: 'docker logout')
                }
            }
        }
    }

    post {
        always {
            script {
                // CI-образ нужен только для проверки сборки, не копим их на диске.
                if (env.CI_IMAGE_TAG) {
                    bat(returnStatus: true, script: "docker image rm -f \"${env.CI_IMAGE_TAG}\"")
                }
            }
        }

        success {
            script {
                if (isMainBranch()) {
                    echo 'CI/CD завершён успешно. Приложение запущено в Docker.'
                    echo 'Сайт доступен по адресу http://localhost/'
                } else {
                    echo 'CI завершён успешно. Деплой не выполнялся: ветка не main.'
                }
            }
        }

        failure {
            echo 'Ошибка CI/CD. Проверьте логи этапа, завершившегося с ошибкой.'
        }
    }
}