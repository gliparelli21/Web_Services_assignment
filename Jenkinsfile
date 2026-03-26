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
                powershell '''
                    $workDir = $env:WORK_DIR
                    $branch = $env:BRANCH
                    $repoUrl = $env:GIT_REPO_URL
                    if (Test-Path $workDir) { Remove-Item -Path $workDir -Recurse -Force }
                    git clone --depth 1 --branch $branch $repoUrl $workDir
                '''
            }
        }

        stage('Build Ubuntu API Container') {
            steps {
                dir("${WORK_DIR}") {
                    powershell '''
                        $network = $env:PIPELINE_NETWORK
                        $container = $env:API_CONTAINER
                        $image = $env:API_IMAGE
                        docker network create $network 2>$null
                        docker rm -f $container 2>$null
                        docker build -t $image -f Dockerfile.api .
                    '''
                }
            }
        }

        stage('Run API Container In Background') {
            steps {
                dir("${WORK_DIR}") {
                    powershell '''
                        $container = $env:API_CONTAINER
                        $network = $env:PIPELINE_NETWORK
                        $mongoUri = $env:MONGODB_URI
                        $dbName = $env:DB_NAME
                        $colName = $env:COLLECTION_NAME
                        $port = $env:API_PORT
                        $image = $env:API_IMAGE
                        docker run -d --name $container --network $network -e MONGODB_URI=$mongoUri -e DB_NAME=$dbName -e COLLECTION_NAME=$colName -p "${port}:8000" $image
                    '''
                }
            }
        }

        stage('Wait For API Readiness') {
            steps {
                dir("${WORK_DIR}") {
                    powershell '''
                        $maxAttempts = 60
                        $container = $env:API_CONTAINER
                        for ($i = 1; $i -le $maxAttempts; $i++) {
                            $result = docker exec $container curl -fsS http://localhost:8000/docs 2>$null
                            if ($LASTEXITCODE -eq 0) {
                                Write-Output "API is ready"
                                exit 0
                            }
                            Write-Output "Attempt $i/$maxAttempts - API not ready yet, waiting..."
                            Start-Sleep -Seconds 2
                        }
                        Write-Output "API failed to start. Last 20 logs:"
                        docker logs $container | Select-Object -Last 20
                        exit 1
                    '''
                }
            }
        }

        stage('Seed MongoDB Data') {
            steps {
                dir("${WORK_DIR}") {
                    powershell '''
                        $container = $env:API_CONTAINER
                        docker exec $container python3 mongodb.py
                    '''
                }
            }
        }

        stage('Run Python Unit Tests') {
            steps {
                dir("${WORK_DIR}") {
                    powershell '''
                        $container = $env:API_CONTAINER
                        docker exec $container python3 -m pytest tests -q
                    '''
                }
            }
        }

        stage('Run Postman Tests With Newman') {
            steps {
                dir("${WORK_DIR}") {
                    powershell '''
                        $container = $env:API_CONTAINER
                        $network = $env:PIPELINE_NETWORK
                        if (-not (Test-Path "reports")) { New-Item -ItemType Directory -Path "reports" | Out-Null }
                        $collection = Get-Content postman/products_api.postman_collection.json -Raw
                        $collection | docker run --rm --network $network -i postman/newman:alpine run /dev/stdin --env-var "baseUrl=http://${container}:8000" --env-var "newProductId=990001" --reporters json,cli --reporter-json-export reports/newman-report.json
                    '''
                }
            }
        }

        stage('Generate README.txt') {
            steps {
                dir("${WORK_DIR}") {
                    powershell '''
                        $container = $env:API_CONTAINER
                        docker exec $container python3 generate_readme_txt.py
                        docker cp "${container}:/app/README.txt" .
                        if (-not (Test-Path "README.txt")) {
                            Write-Error "README.txt not generated"
                            exit 1
                        }
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
