
# Progam made by Chota Mulenga 
# This program is a Flask web application that allows users to search for MAC addresses
# across multiple sites on a UniFi controller. It uses asynchronous requests to improve performance
# and handles session management for user authentication. The application is designed to be run locally
# and provides a simple web interface for users to input MAC addresses and view search results.


# Import necessary libraries
from flask import Flask, request, render_template, redirect, url_for, session, flash
import requests
from requests.exceptions import ConnectionError, Timeout
from flask_session import Session
from concurrent.futures import ThreadPoolExecutor
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import asyncio
import aiohttp
import nest_asyncio
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allow asyncio to run in Flask
nest_asyncio.apply()
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

app = Flask(__name__)

# Session Configuration
app.secret_key = "f3d1b2c6a789e4f56d3a7b89e2f4c678d1e3b9c6a7f8d2e3b4c5d6e7f8a9b0c1"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
Session(app)

# UniFi Controller Details
UNIFI_CONTROLLER = "" #enter your controller URL here
SESSION_REQUESTS = requests.Session()

# Configure connection pooling for the requests session
adapter = requests.adapters.HTTPAdapter(
    pool_connections=20, 
    pool_maxsize=20,
    max_retries=3
)
SESSION_REQUESTS.mount('https://', adapter)
SESSION_REQUESTS.mount('http://', adapter)
SESSION_REQUESTS.verify = False


def unifi_login(username, password):
    """Logs into the UniFi controller and saves the session cookie."""
    login_url = f"{UNIFI_CONTROLLER}/api/login"
    payload = {"username": username, "password": password}
    response = SESSION_REQUESTS.post(login_url, json=payload, verify=False)

    if response.status_code == 200:
        session["logged_in"] = True
        session["username"] = username
        session["password"] = password
        session["cookies"] = SESSION_REQUESTS.cookies.get_dict()
        flash("Login successful!", "success")
        return True
    else:
        flash("Login failed. Check your credentials.", "danger")
        return False


def get_sites():
    """Gets all sites on the controller using the session cookies."""
    url = f"{UNIFI_CONTROLLER}/api/self/sites"
    try:
        response = SESSION_REQUESTS.get(
            url, 
            cookies=session.get("cookies"), 
            verify=False,
            timeout=5
        )
        return response.json().get("data", [])
    except Exception as e:
        logger.error(f"Error getting sites: {e}")
        return []


async def search_site_async(session_async, site, mac_address, cookies, timeout=3):
    """Search for a MAC address in a specific site asynchronouslytouch .gitignore
."""
    site_id = site["name"]
    site_desc = site["desc"]
    url = f"{UNIFI_CONTROLLER}/api/s/{site_id}/stat/device-basic"

    try:
        # Add timeout to prevent hanging connections
        async with session_async.get(url, ssl=False, cookies=cookies, timeout=timeout) as response:
            if response.status == 200:
                devices = (await response.json()).get("data", [])
                for device in devices:
                    if device.get("mac", "").lower() == mac_address.lower():
                        return {"site_name": site_id, "site_desc": site_desc}
            return None
    except asyncio.TimeoutError:
        logger.warning(f"Timeout searching site {site_id}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"Error searching site {site_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error searching site {site_id}: {e}")
        return None


async def search_mac_async(mac_address, cookies):
    """Search for a MAC address across all sites asynchronously with proper task handling."""
    results = []
    sites = get_sites()
    mac_address = mac_address.lower()
    
    # Use a connection limit to prevent overwhelming the server
    conn = aiohttp.TCPConnector(limit=10, ssl=False)
    
    # Configure timeouts for the client session
    timeout = aiohttp.ClientTimeout(total=10, connect=3, sock_connect=3, sock_read=3)
    
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session_async:
        # Create all tasks
        tasks = []
        for site in sites:
            task = asyncio.create_task(
                search_site_async(session_async, site, mac_address, cookies)
            )
            tasks.append(task)
        
        # Gather all completed tasks with timeout protection
        try:
            # Wait for all tasks with a timeout
            for done_task in asyncio.as_completed(tasks, timeout=15):
                try:
                    result = await done_task
                    if result:
                        # Cancel all remaining tasks when we find a match
                        for task in tasks:
                            if not task.done():
                                task.cancel()
                        results.append(result)
                        break
                except Exception as e:
                    logger.error(f"Task error: {e}")
                    continue
        except asyncio.TimeoutError:
            logger.warning("Overall search operation timed out")
            # Cancel any remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
        
        # Wait for all tasks to fully cancel (important to prevent task destroyed errors)
        try:
            pending = [task for task in tasks if not task.done()]
            if pending:
                # Wait for a short time for proper cancellation
                await asyncio.wait(pending, timeout=1)
                
                # Force cancel any still-pending tasks
                for task in pending:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
        except Exception as e:
            logger.error(f"Error during task cleanup: {e}")
    
    return results


def search_mac(mac_address):
    """Wrapper to run the async search with proper event loop handling."""
    cookies = session.get("cookies", {})
    
    # Get or create an event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Record start time for performance monitoring
    start_time = time.time()
    
    try:
        # Run the async function
        results = loop.run_until_complete(search_mac_async(mac_address, cookies))
        
        # Log performance metrics
        duration = time.time() - start_time
        logger.info(f"MAC search completed in {duration:.2f} seconds")
        
        return results
    except Exception as e:
        logger.error(f"Error in search_mac: {e}")
        return []


@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    results = None
    mac_address = ""
    
    if request.method == "POST":
        mac_address = request.form.get("mac_address", "").strip().lower()
        if mac_address:
            try:
                results = search_mac(mac_address)
            except Exception as e:
                flash(f"Error searching: {str(e)}", "danger")
                logger.error(f"Search error: {str(e)}")

    return render_template("index.html", results=results, last_search=mac_address)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if unifi_login(username, password):
            return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)