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
                powershell 'if (Test-Path "${env:WORK_DIR}") { Remove-Item -Path "${env:WORK_DIR}" -Recurse -Force }; git clone --depth 1 --branch "${env:BRANCH}" "${env:GIT_REPO_URL}" "${env:WORK_DIR}"'
            }
        }

        stage('Build Ubuntu API Container') {
            steps {
                dir("${WORK_DIR}") {
                    powershell 'docker network create "${env:PIPELINE_NETWORK}" -ErrorAction SilentlyContinue; docker rm -f "${env:API_CONTAINER}" -ErrorAction SilentlyContinue; docker build -t "${env:API_IMAGE}" -f Dockerfile.api .'
                }
            }
        }

        stage('Run API Container In Background') {
            steps {
                dir("${WORK_DIR}") {
                    powershell "docker run -d --name `"${env:API_CONTAINER}`" --network `"${env:PIPELINE_NETWORK}`" -e MONGODB_URI=`"${env:MONGODB_URI}`" -e DB_NAME=`"${env:DB_NAME}`" -e COLLECTION_NAME=`"${env:COLLECTION_NAME}`" -p ${env:API_PORT}:8000 `"${env:API_IMAGE}`""
                }
            }
        }

        stage('Wait For API Readiness') {
            steps {
                dir("${WORK_DIR}") {
                    powershell '''
                        $maxAttempts = 60
                        for ($i = 1; $i -le $maxAttempts; $i++) {
                            try {
                                docker exec "${env:API_CONTAINER}" curl -fsS http://localhost:8000/docs | Out-Null
                                exit 0
                            } catch {
                                Start-Sleep -Seconds 2
                            }
                        }
                        Write-Output "API failed to start. Last 20 logs:"
                        docker logs "${env:API_CONTAINER}" | Select-Object -Last 20
                        exit 1
                    '''
                }
            }
        }

        stage('Seed MongoDB Data') {
            steps {
                dir("${WORK_DIR}") {
                    powershell 'docker exec "${env:API_CONTAINER}" python3 mongodb.py'
                }
            }
        }

        stage('Run Python Unit Tests') {
            steps {
                dir("${WORK_DIR}") {
                    powershell 'docker exec "${env:API_CONTAINER}" python3 -m pytest tests -q'
                }
            }
        }

        stage('Run Postman Tests With Newman') {
            steps {
                dir("${WORK_DIR}") {
                    powershell '''
                        if (-not (Test-Path "reports")) { New-Item -ItemType Directory -Path "reports" }
                        $collectionContent = Get-Content postman/products_api.postman_collection.json
                        $collectionContent | docker run --rm --network "${env:PIPELINE_NETWORK}" -i postman/newman:alpine run /dev/stdin --env-var "baseUrl=http://${env:API_CONTAINER}:8000" --env-var "newProductId=990001" --reporters json,cli --reporter-json-export reports/newman-report.json
                    '''
                }
            }
        }

        stage('Generate README.txt') {
            steps {
                dir("${WORK_DIR}") {
                    powershell '''
                        docker exec "${env:API_CONTAINER}" python3 generate_readme_txt.py
                        docker cp "${env:API_CONTAINER}:/app/README.txt" .
                        if (-not (Test-Path "README.txt")) { exit 1 }
                    '''
                }
            }
        }
    }

    post {
        always {
            // Cleanup is handled by pipeline teardown
            echo "Pipeline execution completed"
        }
        failure {
            echo "Pipeline failed. Check logs for details."
        }
    }
}
