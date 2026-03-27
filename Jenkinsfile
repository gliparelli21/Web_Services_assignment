pipeline {
    agent any

    options {
        timestamps()
    }

    parameters {
        string(name: 'GIT_REPO_URL', defaultValue: 'https://github.com/gliparelli21/Web_Services_assignment.git', description: 'GitHub repository URL to pull code from')
        string(name: 'BRANCH', defaultValue: 'main', description: 'Git branch to clone')
        string(name: 'DB_NAME', defaultValue: 'products_db', description: 'MongoDB database name')
        string(name: 'COLLECTION_NAME', defaultValue: 'products', description: 'MongoDB collection name')
    }

    environment {
        MONGODB_URI = credentials('mongodb-uri')
        WORK_DIR = 'github-src'
        API_IMAGE = 'ws-assignment-api'
        API_CONTAINER = 'ws-assignment-api-container'
        PIPELINE_NETWORK = 'ws-assignment-net'
        API_PORT = '8000'
    }

    stages {
        stage('Validate Inputs') {
            steps {
                script {
                    if (!params.GIT_REPO_URL?.trim()) {
                        error('GIT_REPO_URL is required.')
                    }
                    if (!env.MONGODB_URI?.trim()) {
                        error('MONGODB_URI credential is required.')
                    }
                }
            }
        }

        stage('Pull Code from GitHub') {
            steps {
                bat '''
                    if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
                    git clone --depth 1 --branch "%BRANCH%" "%GIT_REPO_URL%" "%WORK_DIR%"
                '''
            }
        }

        stage('Build Ubuntu API Container') {
            steps {
                dir("${WORK_DIR}") {
                    bat '''
                        docker network create %PIPELINE_NETWORK% >nul 2>&1 || true
                        docker rm -f %API_CONTAINER% >nul 2>&1 || true
                        docker build -t %API_IMAGE% -f Dockerfile.api .
                    '''
                }
            }
        }

        stage('Run API Container In Background') {
            steps {
                dir("${WORK_DIR}") {
                    bat '''
                        docker run -d ^
                            --name %API_CONTAINER% ^
                            --network %PIPELINE_NETWORK% ^
                            --dns 8.8.8.8 ^
                            --dns 1.1.1.1 ^
                            -e MONGODB_URI=%MONGODB_URI% ^
                            -e DB_NAME=%DB_NAME% ^
                            -e COLLECTION_NAME=%COLLECTION_NAME% ^
                            -p %API_PORT%:8000 ^
                            %API_IMAGE%
                    '''
                }
            }
        }

        stage('Wait For API Readiness') {
            steps {
                dir("${WORK_DIR}") {
                    bat '''
                        setlocal enabledelayedexpansion
                        for /L %%i in (1,1,60) do (
                            docker exec %API_CONTAINER% curl -fsS http://localhost:8000/docs >nul 2>&1
                            if !errorlevel! equ 0 (
                                echo API is ready
                                exit /b 0
                            )
                            timeout /t 2 /nobreak >nul
                        )
                        echo API failed to start
                        docker logs %API_CONTAINER%
                        exit /b 1
                    '''
                }
            }
        }

        stage('Seed MongoDB Data') {
            steps {
                dir("${WORK_DIR}") {
                    bat 'docker exec %API_CONTAINER% python3 mongodb.py'
                }
            }
        }

        stage('Run Python Unit Tests') {
            steps {
                dir("${WORK_DIR}") {
                    bat 'docker exec %API_CONTAINER% python3 -m pytest tests -q'
                }
            }
        }

        stage('Run Postman Tests With Newman') {
            steps {
                dir("${WORK_DIR}") {
                    bat '''
                        setlocal enabledelayedexpansion
                        if not exist reports mkdir reports
                        
                        for /f "delims=" %%A in ('cd') do set "CURRENT_DIR=%%A"
                        
                        docker run --rm ^
                            --network %PIPELINE_NETWORK% ^
                            -v "!CURRENT_DIR!/postman:/postman" ^
                            -v "!CURRENT_DIR!/reports:/reports" ^
                            postman/newman:alpine run /postman/products_api.postman_collection.json ^
                            --env-var "baseUrl=http://%API_CONTAINER%:8000" ^
                            --env-var "newProductId=990001" ^
                            --reporters json,cli ^
                            --reporter-json-export /reports/newman-report.json
                    '''
                }
            }
        }

        stage('Generate README.txt') {
            steps {
                dir("${WORK_DIR}") {
                    bat '''
                        setlocal enabledelayedexpansion
                        
                        REM Run script and capture zip filename
                        for /f "tokens=2 delims==" %%F in ('docker exec %API_CONTAINER% python3 generate_readme_txt.py ^| findstr "ZIPFILE="') do (
                            set "ZIP_FILE=%%F"
                        )
                        
                        docker cp %API_CONTAINER%:/app/README.txt .
                        
                        if defined ZIP_FILE (
                            docker cp %API_CONTAINER%:/app/!ZIP_FILE! .
                        ) else (
                            echo Warning: No zip file generated
                            exit /b 1
                        )
                        
                        if not exist README.txt exit /b 1
                    '''
                }
            }
        }
    }

    post {
        always {
            echo "Pipeline completed. API container remains active at http://localhost:8000/docs"
            archiveArtifacts artifacts: 'github-src/complete-*.zip', allowEmptyArchive: true
        }
        failure {
            echo "Pipeline failed. Check logs for details."
        }
    }
}
