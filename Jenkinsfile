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
                    if (!params.MONGODB_URI?.trim()) {
                        error('MONGODB_URI is required.')
                    }
                }
            }
        }

        stage('Pull Code from GitHub') {
            steps {
                sh 'rm -rf "${WORK_DIR}"; git clone --depth 1 --branch "${BRANCH}" "${GIT_REPO_URL}" "${WORK_DIR}"'
            }
        }

        stage('Build Ubuntu API Container') {
            steps {
                dir("${WORK_DIR}") {
                    sh 'docker network create "${PIPELINE_NETWORK}" >/dev/null 2>&1 || true; docker rm -f "${API_CONTAINER}" >/dev/null 2>&1 || true; docker build -t "${API_IMAGE}" -f Dockerfile.api .'
                }
            }
        }

        stage('Run API Container In Background') {
            steps {
                dir("${WORK_DIR}") {
                    sh '''
                        docker run -d \
                            --name "${API_CONTAINER}" \
                            --network "${PIPELINE_NETWORK}" \
                            -e MONGODB_URI="${MONGODB_URI}" \
                            -e DB_NAME="${DB_NAME}" \
                            -e COLLECTION_NAME="${COLLECTION_NAME}" \
                            -p ${API_PORT}:8000 \
                            "${API_IMAGE}"
                    '''
                }
            }
        }

        stage('Wait For API Readiness') {
            steps {
                dir("${WORK_DIR}") {
                    sh '''
                        for i in $(seq 1 60); do
                            docker exec "${API_CONTAINER}" curl -fsS http://localhost:8000/docs >/dev/null 2>&1 && exit 0
                            sleep 2
                        done
                        echo "API failed to start. Last 20 logs:"
                        docker logs "${API_CONTAINER}" | tail -20
                        exit 1
                    '''
                }
            }
        }

        stage('Seed MongoDB Data') {
            steps {
                dir("${WORK_DIR}") {
                    sh 'docker exec "${API_CONTAINER}" python3 mongodb.py'
                }
            }
        }

        stage('Run Python Unit Tests') {
            steps {
                dir("${WORK_DIR}") {
                    sh 'docker exec "${API_CONTAINER}" env PYTHONPATH=/app pytest -q tests'
                }
            }
        }

        stage('Run Postman Tests With Newman') {
            steps {
                dir("${WORK_DIR}") {
                    sh '''
                        mkdir -p reports
                        cat postman/products_api.postman_collection.json | docker run --rm \
                            --network "${PIPELINE_NETWORK}" \
                            -i \
                            postman/newman:alpine \
                            run /dev/stdin \
                            --env-var "baseUrl=http://${API_CONTAINER}:8000" \
                            --env-var "newProductId=990001" \
                            --reporters json,cli \
                            --reporter-json-export reports/newman-report.json
                    '''
                }
            }
        }

        stage('Generate README.txt') {
            steps {
                dir("${WORK_DIR}") {
                    sh 'docker exec "${API_CONTAINER}" python3 generate_readme_txt.py; docker cp "${API_CONTAINER}:/app/README.txt" "$(pwd)/README.txt"; test -f README.txt'
                }
            }
        }
    }

    post {
        always {
            script {
                sh 'docker rm -f "${API_CONTAINER}" >/dev/null 2>&1 || true; docker network rm "${PIPELINE_NETWORK}" >/dev/null 2>&1 || true'
            }
        }
        failure {
            echo "Pipeline failed. Check logs for details."
        }
    }
}
