FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    docker.io \
    fontconfig \
    git \
    gnupg \
    openjdk-17-jre \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key -o /etc/apt/keyrings/jenkins-keyring.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" > /etc/apt/sources.list.d/jenkins.list \
    && apt-get update \
    && apt-get install -y jenkins \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8080

ENTRYPOINT ["/usr/bin/java", "-jar", "/usr/share/java/jenkins.war"]
