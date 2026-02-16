pipeline {
    agent {
        docker {
            image 'python:3.12-bookworm' // Using the stable Debian-based Python 3.12 image
        }
    }
    
    // This ensures the pipeline only triggers/runs for your specific branch
    stages {
        stage('Checkout') {
            when {
                branch 'refactor/simplize'
            }
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'pip install --upgrade pip'
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                // Setting PYTHONPATH to the current workspace and running pytest
                sh 'PYTHONPATH=. pytest'
            }
        }
    }
    
    post {
        always {
            echo 'Cleaning up workspace...'
        }
        failure {
            echo 'Tests failed! Check the refactor logic.'
        }
    }
}