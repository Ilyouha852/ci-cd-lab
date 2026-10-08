pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install dependencies') {
            steps {
                bat 'python -m pip install --upgrade pip'
                bat 'pip install -r requirements.txt'
            }
        }

        stage('Run tests') {
            steps {
                bat 'python -m pytest tests\ -v'
            }
        }

        stage('Build') {
            steps {
                bat 'python -m py_compile app.py database.py config.py'
            }
        }
    }

    post {
        success {
            echo 'Сборка и тестирование успешно завершены.'
        }

        failure {
            echo 'При сборке или тестировании произошла ошибка.'
        }
    }
}