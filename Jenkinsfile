// Единый pipeline для всех веток.
//   * любая ветка, кроме main: установка зависимостей, тесты, проверка и сборка
//     отдельного CI-образа с уникальным тегом. Деплоя нет, работающее
//     приложение не затрагивается;
//   * ветка main: те же проверки + сборка, публикация на Docker Hub и деплой через
//     Docker Compose, затем сборка образов, деплой в Kubernetes (minikube) и
//     smoke-тест через gateway.
//
// Приложение состоит из двух сервисов (cars-service, owners-service) и gateway;
// у каждого свой Dockerfile, свои тесты и свой образ.
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

    environment {
        // Образы: ${IMAGE_REPO}-cars-service, ${IMAGE_REPO}-owners-service, ${IMAGE_REPO}-gateway
        IMAGE_REPO = 'benjohnson1229/car-accounting'
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
        MINIKUBE_HOME = 'C:\\Users\\ILYOUSHA'
        KUBECONFIG    = 'C:\\Users\\ILYOUSHA\\.kube\\config'
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
                bat 'python -m pip install -r cars-service/requirements.txt -r owners-service/requirements.txt'
            }
        }

        // Модули сервисов называются одинаково (app.py, database.py...), поэтому
        // тесты каждого сервиса запускаются отдельным процессом из своей папки.
        stage('Test cars-service') {
            steps {
                dir('cars-service') {
                    bat 'python -m pytest tests -v'
                }
            }
        }

        stage('Test owners-service') {
            steps {
                dir('owners-service') {
                    bat 'python -m pytest tests -v'
                }
            }
        }

        stage('Build') {
            steps {
                bat 'python -m py_compile cars-service/app.py cars-service/clients.py cars-service/database.py cars-service/config.py'
                bat 'python -m py_compile owners-service/app.py owners-service/clients.py owners-service/database.py owners-service/config.py'
                bat 'docker compose config -q'
            }
        }

        // Не main: образы с уникальным тегом, чтобы не перезаписать образы
        // работающего приложения.
        stage('Build CI Docker images') {
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

                    env.CI_IMAGE_TAG = "${branchTag}-${env.BUILD_NUMBER}"
                }

                // Docker Hub иногда отвечает TLS handshake timeout, поэтому повторы.
                retry(3) {
                    bat "docker build -t car-accounting-ci/cars-service:${env.CI_IMAGE_TAG} cars-service"
                    bat "docker build -t car-accounting-ci/owners-service:${env.CI_IMAGE_TAG} owners-service"
                    bat "docker build -t car-accounting-ci/gateway:${env.CI_IMAGE_TAG} gateway"
                }
            }
        }

        stage('Deploy with Docker Compose') {
            when {
                expression { return isMainBranch() }
            }

            environment {
                // Jenkins: Credentials -> Username with password
                // (логин Docker Hub + Access Token), ID = dockerhub-credentials.
                // Создаёт DOCKERHUB_USR и DOCKERHUB_PSW (в логе маскируются).
                DOCKERHUB = credentials('dockerhub-credentials')
            }

            steps {
                // Сборка трёх образов (cars-service, owners-service, gateway) и
                // публикация на Docker Hub: тег = номер сборки и latest.
                // В bat код возврата берётся только от последней команды,
                // поэтому после каждой стоит || exit /b 1.
                retry(2) {
                    bat '''
                        @echo off
                        echo %DOCKERHUB_PSW%| docker login -u %DOCKERHUB_USR% --password-stdin || exit /b 1
                        docker compose -p caraccounting build cars-service owners-service gateway || exit /b 1
                        docker compose -p caraccounting push cars-service owners-service gateway || exit /b 1
                        for %%S in (cars-service owners-service gateway) do (
                            docker tag %IMAGE_REPO%-%%S:%IMAGE_TAG% %IMAGE_REPO%-%%S:latest || exit /b 1
                            docker push %IMAGE_REPO%-%%S:latest || exit /b 1
                        )
                    '''
                }

                powershell '''
                    $ErrorActionPreference = "Stop"
                    Set-Location $env:WORKSPACE

                    Write-Host "Starting cars-service, owners-service and gateway..."

                    # --remove-orphans убирает контейнеры прежней версии (app, nginx):
                    # иначе старый nginx продолжит занимать порт 80.
                    docker compose -p caraccounting up -d --remove-orphans
                    if ($LASTEXITCODE -ne 0) {
                        throw "Docker Compose deployment failed"
                    }

                    Write-Host "Waiting for the website..."

                    $ready = $false

                    for ($i = 0; $i -lt 30; $i++) {
                        Start-Sleep -Seconds 2

                        try {
                            # главная и список автомобилей отдаёт cars-service,
                            # /owners/ - owners-service: проверяем оба сервиса через gateway
                            $codes = foreach ($u in "http://localhost/", "http://localhost/owners/") {
                                (Invoke-WebRequest -Uri $u -TimeoutSec 3 -UseBasicParsing).StatusCode
                            }

                            if (($codes | Where-Object { $_ -ne 200 }).Count -eq 0) {
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

        // Kubernetes (minikube): только main. Требования к агенту: установлены
        // minikube и kubectl, кластер запущен (minikube start), у пользователя
        // службы Jenkins доступен kubeconfig (при необходимости задайте KUBECONFIG).
        // Образы собираются локально и загружаются в minikube (minikube image load),
        // внешний реестр не нужен. Тег образов = номер сборки.
        stage('Build images for Kubernetes') {
            when {
                expression { return isMainBranch() }
            }
            steps {
                retry(3) {
                    bat 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1 -Tag %BUILD_NUMBER%'
                }
            }
        }

        stage('Deploy to Kubernetes') {
            when {
                expression { return isMainBranch() }
            }
            steps {
                bat 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy.ps1 -Tag %BUILD_NUMBER%'
            }
        }

        stage('Smoke test (Kubernetes)') {
            when {
                expression { return isMainBranch() }
            }
            steps {
                bat 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke.ps1'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/results.xml'
                }
            }
        }
    }

    post {
        always {
            script {
                if (isMainBranch()) {
                    bat(returnStatus: true, script: 'docker logout')
                }
                // CI-образы нужны только для проверки сборки, не копим их на диске.
                if (env.CI_IMAGE_TAG) {
                    for (svc in ['cars-service', 'owners-service', 'gateway']) {
                        bat(returnStatus: true, script: "docker image rm -f car-accounting-ci/${svc}:${env.CI_IMAGE_TAG}")
                    }
                }
            }
        }

        success {
            script {
                if (isMainBranch()) {
                    echo 'CI/CD завершён успешно. Приложение запущено в Docker.'
                    echo 'Сайт доступен по адресу http://localhost/'
                    echo 'Kubernetes: kubectl port-forward -n car-accounting svc/gateway 8082:80, сайт http://localhost:8082/'
                } else {
                    echo 'CI завершён успешно. Деплой не выполнялся: ветка не main.'
                }
            }
        }

        failure {
            echo 'Ошибка CI/CD. Проверьте логи этапа, завершившегося с ошибкой.'
            script {
                if (isMainBranch()) {
                    bat(returnStatus: true, script: 'kubectl get pods -n car-accounting')
                }
            }
        }
    }
}