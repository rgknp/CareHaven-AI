# Example usage in your main script
async def main():
    # Make sure to call load_dotenv() at the beginning of your main script
    # from dotenv import load_dotenv
    # load_dotenv()

    try:
        event_grid_client = EventGridClient()
        
        events_to_send = [
            {
                "id": "e70d4c1b-e52b-4d43-982d-114d4a8d0b5e",
                "agent_id": "abnormal_heart_rate_agent",
                "event_type": "high_heart_rate",
                "severity": "critical",
                "patient_id": "patient-12345",
                "value": 150
            }
        ]
        
        event_grid_client.publish(events_to_send)

    except ValueError as e:
        logger.error(f"Configuration error: {e}. Please check your .env file.")

if __name__ == "__main__":
    # This is how you would run it in a real application
    # async run isn't necessary for a sync function like this, but good practice
    # in an async codebase
    main()