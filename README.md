## Docker deployment

This repository contains a FastAPI backend and a React/Vite frontend. The backend image runs on port 8000. The frontend image builds the React application and serves it with Nginx on port 80. Nginx proxies the API routes to the backend container, so production browser requests do not use `localhost`.

Run locally from this directory:

```bash
docker compose up --build
```

Open `http://localhost:8080` and verify the health endpoint at `http://localhost:8080/health`.

## AWS deployment path

For a first company proof of concept, run this Compose stack on a private-subnet EC2 instance behind an Application Load Balancer. Open only ports 80/443 on the load balancer security group; do not expose backend port 8000 publicly.

For production, push the two images to private ECR repositories and run them as ECS Fargate services. Use an ALB for the frontend, private subnets for ECS tasks, RDS PostgreSQL for metadata, S3 for uploaded/generated files, Secrets Manager for credentials, ACM for HTTPS, WAF for the ALB, and CloudWatch for logs.

Build the images:

```bash
docker build -f backend/Dockerfile -t ecc-migration-backend .
docker build -f frontend/Dockerfile -t ecc-migration-frontend ./frontend
```

The current application keeps sessions and generated downloads in memory. That is acceptable for an initial single-instance test, but persistence in S3/PostgreSQL is required before running multiple ECS tasks or relying on files after a restart.
