pipeline {
    agent {
        docker {
            image 'hgnguyen37/python-ffmpeg-pytest:3.12-slim-stable' // Using the custom python:3.12 with ffmpeg
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

        stage('Install dependencies') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Lint') {
            steps {
                sh 'ruff check .'
            }
        }

        stage('Run Unit Tests') {
            steps {
                sh 'pytest -m unit -s --html=report-unit.html --self-contained-html --junitxml=results-unit.xml --cov=app --cov-report=html --cov-fail-under=80'
            }
            post {
                always {
                    junit testResults: 'results-unit.xml', skipPublishingChecks: true
                }
            }
        }

        stage('Run Integration Tests') {
            steps {
                sh 'pytest -m integration -s --html=report-integration.html --self-contained-html --junitxml=results-integration.xml'
            }
            post {
                always {
                    junit testResults: 'results-integration.xml', skipPublishingChecks: true
                }
            }
        }

        stage('Run E2E Tests') {
            steps {
                sh 'pytest -m e2e -s --html=report-e2e.html --self-contained-html --junitxml=results-e2e.xml'
            }
            post {
                always {
                    junit testResults: 'results-e2e.xml', skipPublishingChecks: true
                }
            }
        }
    }
    
    post {
        always {            
            // Optional: Store the pretty HTML report as an artifact
            archiveArtifacts artifacts: 'report-unit.html', fingerprint: true
            archiveArtifacts artifacts: 'report-integration.html', fingerprint: true
            archiveArtifacts artifacts: 'report-e2e.html', fingerprint: true

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