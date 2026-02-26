"""Configuration - 공유 설정

인증 우선순위:
1. AZURE_OPENAI_API_KEY 환경변수가 있으면 API Key 인증
2. 없으면 DefaultAzureCredential (AKS Workload Identity / Service Connector)
"""
import os
from dotenv import load_dotenv

load_dotenv()

# === Azure OpenAI ===
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")  # Optional: 없으면 DefaultAzureCredential 사용

if not AZURE_OPENAI_ENDPOINT:
    raise RuntimeError(
        "Missing required environment variable: AZURE_OPENAI_ENDPOINT. "
        "Set this before starting the application."
    )

# DefaultAzureCredential 사용 여부 (API Key 없을 때)
USE_DEFAULT_CREDENTIAL = not AZURE_OPENAI_API_KEY

if USE_DEFAULT_CREDENTIAL:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    _credential = DefaultAzureCredential()
    AZURE_TOKEN_PROVIDER = get_bearer_token_provider(
        _credential, "https://cognitiveservices.azure.com/.default"
    )
else:
    AZURE_TOKEN_PROVIDER = None

AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

# === OpenTelemetry ===
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
