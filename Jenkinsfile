pipeline {
    agent any
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Build') { steps { bat 'py -m pip install -r requirements.txt' } }
        stage('Test') { steps { bat 'py -m pytest -v' } }
        stage('Deploy') { steps { echo 'Deploy: приложение прошло сборку и тестирование.'; echo 'Для локального запуска: py app.py' } }
    }
    post { always { echo 'Pipeline completed.' } }
}
