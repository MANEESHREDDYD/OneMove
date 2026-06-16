# OneMove Risk Service

This is an optional portfolio subsystem demonstrating enterprise backend service integration.
It is built with Java and Spring Boot.

## Purpose
- Fraud/risk scoring API (`POST /risk/score-order`)
- Order lifecycle validation (`POST /risk/validate-transition`)
- Demonstrates enterprise-scale microservice isolation.

## Running Locally
This module is not required for the core Next.js application to run.
If you have Java 17+ and Maven installed:

```bash
mvn clean package
mvn test
mvn spring-boot:run
```
