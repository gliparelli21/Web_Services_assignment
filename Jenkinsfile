pipeline {
    agent any

    options {
        timestamps()
    }

    parameters {
        string(name: 'GIT_REPO_URL', defaultValue: '', description: 'GitHub repository URL to pull code from')
        string(name: 'BRANCH', defaultValue: 'main', description: 'Git branch to clone')
        string(name: 'MONGODB_URI', defaultValue: '', description: 'MongoDB connection string used by the API container')
        string(name: 'DB_NAME', defaultValue: 'products_db', description: 'MongoDB database name')
        string(name: 'COLLECTION_NAME', defaultValue: 'products', description: 'MongoDB collection name')
    }

    environment {
        WORK_DIR = 'github-src'
        API_IMAGE = 'ws-assignment-api'
        API_CONTAINER = 'ws-assignment-api-container'
        PIPELINE_NETWORK = 'ws-assignment-net'
        API_PORT = '8000'
        NORMALIZED_REPO_URL = ''
    }

    stages {
        stage('Validate Inputs') {
            steps {
                script {
                    if (!params.GIT_REPO_URL?.trim()) {
                        error('GIT_REPO_URL is required for the GitHub pull step.')
                    }
                    if (!params.MONGODB_URI?.trim()) {
                        error('MONGODB_URI is required so the API can access MongoDB during tests.')
                    }

                    def rawRepo = params.GIT_REPO_URL.trim()
                    if (rawRepo ==~ /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/) {
                        env.NORMALIZED_REPO_URL = "https://github.com/${rawRepo}.git"
                    } else {
                        env.NORMALIZED_REPO_URL = rawRepo
                    }
                }
            }
        }

        stage('Pull Code from GitHub') {
            steps {
                sh '''
                    rm -rf "${WORK_DIR}"
                    git clone --depth 1 --branch "${BRANCH}" "${NORMALIZED_REPO_URL}" "${WORK_DIR}" || {
                        echo "Failed to clone repository: ${NORMALIZED_REPO_URL}"
                        echo "Use either owner/repo or a full URL like https://github.com/owner/repo.git"
                        exit 1
                    }
                '''
            }
        }

        stage('Build Ubuntu API Container') {
            steps {
                dir("${WORK_DIR}") {
                    sh '''
                        docker network create "${PIPELINE_NETWORK}" >/dev/null 2>&1 || true
                        docker rm -f "${API_CONTAINER}" >/dev/null 2>&1 || true
                        docker build -t "${API_IMAGE}" -f Dockerfile.api .
                    '''
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
                        for i in $(seq 1 30); do
                            if docker exec "${API_CONTAINER}" curl -fsS http://localhost:8000/docs >/dev/null 2>&1; then
                                exit 0
                            fi
                            sleep 2
                        done

                        echo "API did not become ready in time."
                        exit 1
                    '''
                }
            }
        }

        stage('Seed MongoDB Data') {
            steps {
                dir("${WORK_DIR}") {
                    sh 'docker exec "${API_CONTAINER}" python3 upload_to_mongodb.py'
                }
            }
        }

        stage('Run Python Unit Tests') {
            steps {
                dir("${WORK_DIR}") {
                    sh 'docker exec "${API_CONTAINER}" pytest -q tests'
                }
            }
        }

        stage('Run Postman Tests With Newman') {
            steps {
                dir("${WORK_DIR}") {
                    sh '''
                        docker run --rm \
                            --network "${PIPELINE_NETWORK}" \
                            -v "$(pwd)/postman:/etc/newman" \
                            postman/newman:alpine \
                            run /etc/newman/products_api.postman_collection.json \
                            --env-var "baseUrl=http://${API_CONTAINER}:8000" \
                            --env-var "newProductId=990001"
                    '''
                }
            }
        }

        stage('Generate README.txt') {
            steps {
                dir("${WORK_DIR}") {
                    sh '''
                        docker exec "${API_CONTAINER}" python3 generate_readme_txt.py
                        docker cp "${API_CONTAINER}:/app/README.txt" "$(pwd)/README.txt"
                        test -f README.txt
                    '''
                }
            }
        }
    }

    post {
        always {
            sh '''
                docker rm -f "${API_CONTAINER}" >/dev/null 2>&1 || true
                docker network rm "${PIPELINE_NETWORK}" >/dev/null 2>&1 || true
            '''
        }
    }
}
