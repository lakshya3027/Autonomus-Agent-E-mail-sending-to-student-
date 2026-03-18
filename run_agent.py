import time

from app.email.email_listener import EmailListener
from app.orchestrator.agent_manager import AgentManager


CHECK_INTERVAL = 30  # seconds


def main():

    listener = EmailListener()
    manager = AgentManager()

    print("🤖 Autonomous Email Agent Started...")

    listener.connect()

    try:
        while True:
            print("\n🔎 Checking for new emails...")

            emails = listener.fetch_unread()

            for email_data in emails:
                manager.run_pipeline(email_data)

            # wait before checking again
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Agent stopped manually.")

    finally:
        listener.close()


if __name__ == "__main__":
    main()