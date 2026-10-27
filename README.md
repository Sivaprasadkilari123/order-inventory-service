# Order & Inventory Management Service

![CI](https://github.com/YOUR_GITHUB_USERNAME/order-inventory-service/actions/workflows/ci.yml/badge.svg)

REST API for multi-warehouse inventory, customers and orders, built with **FastAPI** and **MySQL**.

## Features
- Normalized MySQL schema: customers, warehouses, products, per-warehouse inventory, orders, order items
- JWT authentication (bcrypt password hashing); every business endpoint is protected
- **Atomic orders**: stock deduction and order creation happen in one database transaction, so they succeed or fail together
- Row-level locking (`SELECT ... FOR UPDATE`) prevents overselling under concurrent orders
- Order cancellation restores stock in the same transaction
- Order lines store the price paid, so later price changes don't alter past orders
- pytest suite (auth, CRUD, transactions, rollback, concurrency)
- Docker + docker-compose; GitHub Actions runs lint + tests on every push

## Tech stack
Python 3.12, FastAPI, SQLAlchemy, MySQL 8, JWT (python-jose), pytest, ruff, Docker, GitHub Actions

## Schema
