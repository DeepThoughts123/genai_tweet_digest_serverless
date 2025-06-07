# Quick Start Guide for Newcomers

Welcome to the **GenAI Tweet Digest** project! This guide is designed to get you up to speed on our architecture, codebase, and processes as quickly as possible.

Following this guide will give you a comprehensive understanding of what we're building, what has been done, the structure of the codebase, and how to find any information you need.

---

### 🚀 **Part 1: The "5-Minute" High-Level Overview**

Start with these four documents to get a solid, high-level understanding of the project.

#### 1. **Project README (`README.md`)**
*   **Location**: Project root directory.
*   **Purpose**: This is the 30,000-foot view of the project. It answers: *What is this project and what does it do?*
*   **What you'll learn**:
    *   The project's mission and goals.
    *   A high-level diagram of our hybrid Lambda + Fargate architecture.
    *   A visual overview of the new, clean folder structure.
    *   Quick start commands for initial setup and development.

#### 2. **Documentation Hub (`docs/README.md`)**
*   **Location**: `docs/`
*   **Purpose**: This is the master index for all our documentation. It answers: *Where do I find information about X?*
*   **What you'll learn**:
    *   How to navigate the entire `docs` folder.
    *   A categorized list of all key documents (Architecture, Deployment, Development, etc.).
    *   This is your map for finding any specific information you need in the future.

#### 3. **Codebase Structure (`docs/CODEBASE_STRUCTURE.md`)**
*   **Location**: `docs/`
*   **Purpose**: This is the blueprint of our codebase. It answers: *How is the code organized and why?*
*   **What you'll learn**:
    *   A detailed breakdown of the `src/` directory.
    *   The specific roles of `lambda_functions`, `fargate`, and `shared` libraries.
    *   How different backend components interact with each other.

#### 4. **Product Requirements Document (`planning/product_requirement_document.md`)**
*   **Location**: `planning/`
*   **Purpose**: This document explains the "why" behind the project's features. It answers: *What are the project's features and business goals?*
*   **What you'll learn**:
    *   The project's target audience.
    *   The core features we've implemented (e.g., tweet curation, AI summarization, email distribution).
    *   The business and technical requirements that have shaped the application from the start.