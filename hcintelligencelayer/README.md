Healthcare (HC) Intelligence Core
A plug-and-play intelligence architecture for configuring, deploying, and running AI agents on batch and streaming
healthcare data.

This project provides a foundational Python package for building a healthcare intelligence layer. It implements a plug-and-play architecture where new AI agents can be deployed to process clinical and IoT data,
generate high-value notifications, and publish those high-value events for downstream consumption.

Features
Plug-and-Play Agent System: Easily deploy new AI agents without modifying the core system.

Modular Data Sources: Abstract interfaces for connecting to various data sources, including clinical data (FHIR, DICOM) and IoT streams.

Configurable Agents: Each agent can be configured independently, including its prediction interval and the tools it uses.

Event-Driven Architecture: Agents publish high-value events to a central event hub, which can be consumed by real-time notification systems.

Clear Abstractions: The package provides well-defined abstractions for Agents, DataSources, and EventHub to ensure code is clean and maintainable.

Installation
To install the package, clone the repository and install it in your environment.

Bash

git clone https://github.com/rgknp/CareHaven-AI.git
cd hcintelligencelayer
pip install .
Usage
1. Configure an Agent
Create a configuration file (e.g., config.json) that specifies the agents you want to deploy and their settings.

JSON

{
  "agents": [
    {
      "agent_id": "heart_rate_monitor_01",
      "agent_class": "healthcare_intelligence.agents.abnormal_heart_rate.AbnormalHeartRateAgent",
      "prediction_interval_seconds": 10,
      "config": {
        "threshold_bpm": 120,
        "data_sources": {
          "iot": {
            "source_type": "IOT"
          }
        }
      }
    }
  ],
  "data_sources": {
    "IOT": {
      "host": "iot.hub.example.com",
      "port": 9092
    },
    "FHIR": {
      "endpoint": "https://fhir.server.com/api"
    }
  }
}
2. Run the System
Use the core.manager.py to initialize and run your agents based on the configuration.

Python

from healthcare_intelligence.core.manager import AgentManager
import json

# Load the configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Initialize the manager
manager = AgentManager(config)

# Start the agents
manager.start_all_agents()

Contributing
We welcome contributions! To get started:

Fork the repository.

Create a new branch for your feature (git checkout -b feature/my-new-agent).

Add your code, following the existing file structure and coding standards.

Write tests for your new code.

Submit a pull request with a clear description of your changes.

For a new AI agent, create a new file in the agents/ directory and ensure it inherits from healthcare_intelligence.agents.base_agent.Agent.

