async def main():
    # Now, instantiate the client without passing secrets as arguments
    try:
        client = AzureEventHubClient()
        
        # Example of publishing events
        events_to_send = [
            {"agent_id": "heart_rate_01", "event_type": "abnormal_heart_rate", "value": 150}
        ]
        await client.publish(events_to_send)

    except ValueError as e:
        print(f"Configuration error: {e}. Please check your .env file.")
        
if __name__ == "__main__":
    asyncio.run(main())