# GenAI Tweet Digest - Hybrid Serverless Architecture

> **A cost-effective, scalable tweet digest service using AWS Lambda + Fargate hybrid architecture**

## 🏗️ Architecture Overview

This project implements a **hybrid serverless architecture** that combines the best of both worlds:

- **⚡ Fast Track (Lambda)**: Text-only processing, email distribution, subscriptions (< 15 minutes)
- **🐳 Slow Track (Fargate)**: Visual tweet capture, browser automation (unlimited time)
- **📦 Shared Libraries**: Common functionality used by both tracks

## 📁 Project Structure

```
genai_tweet_digest_serverless/
├── src/                               # 🔥 All application source code
│   ├── shared/                        # 📦 Shared libraries
│   ├── lambda_functions/              # ⚡ Lambda functions (fast track)
│   ├── fargate/                       # 🐳 Fargate containers (slow track)
│   └── frontend/                      # 🌐 Static website
├── infrastructure/                    # ☁️ Infrastructure as Code
├── deployment/                        # 🚀 Deployment automation
├── config/                           # 📋 Configuration files
├── docs/                            # 📚 Documentation
├── tests/                           # 🧪 Test suite
├── tools/                          # 🔧 Development tools
└── archive/                        # 📦 Legacy/reference code
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- AWS CLI configured
- Docker (for Fargate containers)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd genai_tweet_digest_serverless
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.template .env
# Edit .env with your API keys and AWS settings
```

### 3. Deploy Infrastructure
```bash
cd deployment/scripts
./deploy-full.sh
```

## 🏛️ Architecture Components

### Lambda Functions (Fast Track)
- **Weekly Digest**: Main digest generation and email distribution
- **Subscription**: Email subscription management
- **Email Verification**: Email confirmation handling
- **Unsubscribe**: Unsubscribe request processing
- **Fargate Dispatcher**: Launches Fargate tasks for visual processing

### Fargate Containers (Slow Track)
- **Visual Processor**: Browser automation for tweet screenshots
- **Batch Processor**: Future expansion for other long-running tasks

### Shared Libraries
- **Tweet Services**: Twitter API integration, AI categorization
- **Database Services**: DynamoDB operations
- **Email Services**: Amazon SES integration
- **Visual Capture**: Selenium-based screenshot service
- **Processing Orchestrator**: Intelligent routing between Lambda/Fargate

## 📊 Cost Analysis

| Component | Monthly Cost (estimated) |
|-----------|-------------------------|
| Lambda (current) | ~$0.13 |
| Fargate (on-demand) | ~$1.60 |
| **Total Hybrid** | **~$1.73** |

*Costs scale with usage. Fargate only runs when visual processing is needed.*

## 🔧 Development

### Running Tests
```bash
# Unit tests
pytest tests/unit/

# Integration tests  
pytest tests/integration/

# All tests
pytest
```

### Local Development
```bash
# Start local services
cd tools/local-dev
docker-compose up

# Run Lambda function locally
cd src/lambda_functions/weekly_digest
python handler.py
```

### Building Fargate Containers
```bash
cd src/fargate/visual_processor
docker build -t visual-processor .
docker run visual-processor --accounts openai andrewyng --max-tweets 5
```

## 📚 Documentation

- **[Architecture Design](docs/architecture/hybrid-design.md)** - Detailed system architecture
- **[Deployment Guide](docs/deployment/quick-start.md)** - Step-by-step deployment
- **[Development Setup](docs/development/setup.md)** - Local development environment
- **[API Documentation](docs/api/lambda-apis.md)** - API reference

## 🔄 Migration from Previous Structure

This project was recently reorganized for better maintainability. See:
- **[Migration Log](planning/migration_log.md)** - Complete change documentation
- **[New Structure Design](planning/new_project_structure.md)** - Architecture rationale

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation**: [docs/](docs/)
- **Architecture Questions**: See [docs/architecture/](docs/architecture/)

---

**Built with ❤️ for the GenAI community** 