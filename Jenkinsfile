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
                        
                        echo Testing API convert endpoint directly before Newman:
                        docker exec %API_CONTAINER% curl -v http://localhost:8000/convert/990001 2>&1 || echo "Direct test failed"
                        
                        echo Running Newman tests with verbose output...
                        docker run --rm ^
                            --network %PIPELINE_NETWORK% ^
                            -v "!CURRENT_DIR!/postman:/postman" ^
                            -v "!CURRENT_DIR!/reports:/reports" ^
                            postman/newman:alpine run /postman/products_api.postman_collection.json ^
                            --env-var "baseUrl=http://%API_CONTAINER%:8000" ^
                            --env-var "newProductId=990001" ^
                            --reporters json,cli ^
                            --reporter-json-export /reports/newman-report.json ^
                            -v
                    '''
                }
            }
        }

        stage('Generate README.txt') {
            steps {
                dir("${WORK_DIR}") {
                    bat '''
                        docker exec %API_CONTAINER% python3 generate_readme_txt.py
                        docker cp %API_CONTAINER%:/app/README.txt .
                        if not exist README.txt exit /b 1
                    '''
                }
            }
        }
    }

    post {
        always {
            bat 'docker rm -f %API_CONTAINER% >nul 2>&1 || true; docker network rm %PIPELINE_NETWORK% >nul 2>&1 || true'
        }
        failure {
            echo "Pipeline failed. Check logs for details."
        }
    }
}
