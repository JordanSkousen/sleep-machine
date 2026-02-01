import datetime
import os
import uuid
import requests

class EightSleep:
    """
    A client to interact with the Eight Sleep API.
    Handles authentication and provides methods to control the pod.
    """
    def __init__(self):
        """
        Initializes the client by authenticating and fetching the user ID.
        """
        self.username = os.getenv("EIGHTSLEEP_USERNAME")
        self.password = os.getenv("EIGHTSLEEP_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("EIGHTSLEEP_USERNAME and EIGHTSLEEP_PASSWORD environment variables must be set.")

        self.access_token = None
        try:
            self._login()
            self.user_id = self._get_user_id()
        except:
            print("Failed to login to Eight Sleep")
        self.is_pod_on = False
        print("Eight Sleep client initialized successfully.")

    def _get_headers(self) -> dict:
        """
        Constructs the mock headers for API requests to disguise ourselves as the app.
        """
        headers = {
            "Accept": "application/json",
            "X-Client-Session-Id": "ae9aea27-f165-4599-9023-782b1db9988d",
            "baggage": "sentry-environment=production,sentry-public_key=51b2643724f7b9dc3bf5956882cc2be6,sentry-release=com.eightsleep.Eight%407.42.1%2B2,sentry-trace_id=b0b80b7aee454eb29d47078e0e953c4e",
            "X-Client-Device-Id": "4ae79685-1d52-4aff-b75a-8a8a60995fe7",
            "sentry-trace": "b0b80b7aee454eb29d47078e0e953c4e-8f776c682e8e4c72-0",
            "Accept-Language": "en-US;q=1.0",
            "X-Client-App-Version": "7.42.1",
            "User-Agent": "iOS App - 7.42.1/2 - iPhone 12 Pro - iOS 18.0.1",
            "X-Client-Request-Id": f"{uuid.uuid4()}",
            "Content-Type": "application/json",
            "Host": "auth-api.8slp.net",
            "Connection": "keep-alive"
        }
        if self.access_token != None:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _login(self) -> str:
        """
        Logs into the Eight Sleep API to retrieve an access token.
        """
        print("Logging in to Eight Sleep...")
        url = "https://auth-api.8slp.net/v1/tokens"
        headers = self._get_headers()
        data = {
            "client_secret": "f0954a3ed5763ba3d06834c73731a32f15f168f47d4f164751275def86db0c76",
            "client_id": "0894c7f33bb94800a03f1f4df13a4f38",
            "grant_type": "password",
            "username": self.username, 
            "password": self.password,
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        self.access_token = response.json().get("access_token")
        if not self.access_token:
            raise ValueError("Failed to retrieve access_token from login response.")
        
        print("Login successful.")
        self.token_expiry = datetime.datetime.now()
        self.token_expiry += datetime.timedelta(seconds = response.json().get("expires_in"))

    def _get_user_id(self) -> str:
        """
        Retrieves the user's ID from the Eight Sleep API.
        """
        print("Fetching user ID...")
        url = "https://client-api.8slp.net/v1/users/me"
        headers = self._get_headers()
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        user_id = response.json().get("user", {}).get("userId")
        if not user_id:
            raise ValueError("Failed to retrieve user_id from user data.")
        
        print(f"User ID found: {user_id}")
        return user_id
    
    def _check_login_needed(self):
        if datetime.datetime.now() >= self.token_expiry:
            self._login()

    def set_pod_state(self, on):
        """
        Sends a command to turn on the pod.
        """
        print("Sending command to turn ON the pod..." if on else "Sending command to turn OFF the pod...")
        self._check_login_needed()
        url = f"https://app-api.8slp.net/v1/users/{self.user_id}/temperature/pod?ignoreDeviceErrors=false"
        headers = self._get_headers()
        
        response = requests.put(url, headers=headers, json={
            "currentState": {
                "type": "smart" if on else "off"
            }
        })
        response.raise_for_status()
        
        self.is_pod_on = on
        print("Pod 'turn on' command sent successfully." if on else "Pod 'turn off' command sent successfully.")
        return response.json()

    def set_temperature(self, level: int = 0):
        """
        Sends a command to change the temperature of the pod.

        Args:
            level (int): The temperature level for the pod (-100 to 100).
        """
        print(f"Sending command to set temperature to {level}...")
        self._check_login_needed()
        url = f"https://app-api.8slp.net/v1/users/{self.user_id}/temperature/pod?ignoreDeviceErrors=false"
        headers = self._get_headers()

        response = requests.put(url, headers=headers, json={
            "currentLevel": level
        })
        response.raise_for_status()
        
        print("Pod temperature set successfully.")
        return response.json()


if __name__ == '__main__':
    print("--- Running Eight Sleep API Example ---")
    try:
        # The client will automatically log in and get the user ID upon initialization.
        client = EightSleep()
        
        # Step 3: Turn on the pod
        client.set_pod_state(False)
        
        # Step 4: Change the temperature of the pod
        client.set_temperature(level=-45)
        
        print("\n--- Eight Sleep API Example Finished ---")

    except ValueError as e:
        print(f"\n[ERROR] Configuration Error: {e}")
        print("Please ensure EIGHTSLEEP_USERNAME and EIGHTSLEEP_PASSWORD are set as environment variables.")
    except requests.exceptions.HTTPError as e:
        print(f"\n[ERROR] HTTP Error: {e.response.status_code} {e.response.reason}")
        print(f"Response Body: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Network Error: {e}")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
