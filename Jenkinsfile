pipeline {
    agent {
        docker {
            image 'hgnguyen37/python-ffmpeg:3.12-slim' // Using the custom python:3.12 with ffmpeg
        }
    }

    triggers {
        githubPush()
    }
    
    // This ensures the pipeline only triggers/runs for your specific branch
    stages {
        stage('Checkout docker images') {
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
                sh 'pytest -s --html=report.html --self-contained-html --junitxml=results.xml --cov=app --cov-report=html --cov-fail-under=75 || true'
            }
        }
    }
    
    post {
        always {
            // This plugin renders the 'Test Result' tab in Jenkins
            junit testResults:'results.xml', skipPublishingChecks: true
            
            // Optional: Store the pretty HTML report as an artifact
            archiveArtifacts artifacts: 'report.html', fingerprint: true

            publishHTML([
                reportDir: 'htmlcov',
                reportFiles: 'index.html',
                reportName: 'Coverage Report',
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true
            ])
        }
    }
}