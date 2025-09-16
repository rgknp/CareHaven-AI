import os
import importlib
from dotenv import load_dotenv

# --- Step 1: Load the environment-specific .env file ---
ENVIRONMENT = os.getenv("APP_ENV", "dev")
dotenv_path = f'.env.{ENVIRONMENT}'
load_dotenv(dotenv_path=dotenv_path)

# --- Step 3: Your core application logic follows ---
class AgentManager:
    def __init__(self, config):
        self.config = config
        self.agents = []

    def start_all_agents(self):
        for agent_config in self.config.get("agents", []):
            agent_class_path = agent_config["agent_class"]
            module_name, class_name = agent_class_path.rsplit('.', 1)

            # Dynamically import the agent class
            agent_module = importlib.import_module(module_name)
            AgentClass = getattr(agent_module, class_name)
            
            # Initialize and start the agent
            agent = AgentClass(
                agent_id=agent_config["agent_id"],
                config=agent_config["config"]
            )
            self.agents.append(agent)
            print(f"Agent '{agent.agent_id}' initialized.")

if __name__ == "__main__":
    # In a real-world scenario, you would load the config from a file
    # For this example, we'll use a placeholder dictionary
    config = {
        "agents": [
            {
                "agent_id": "heart_rate_monitor_01",
                "agent_class": "healthcare_intelligence.agents.abnormal_heart_rate.AbnormalHeartRateAgent",
                "config": {}
            }
        ]
    }
    
    manager = AgentManager(config)
    manager.start_all_agents()