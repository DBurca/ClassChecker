# Version 3.2

import requests
import websocket, ssl
import time
import json
from datetime import datetime
import random

# ================================
# DISCORD INTEGRATION CLASSES
# ================================
class numbers:
    nums = 10

class discord_integration:
    run_condition = True

# ================================
# CONFIGURATION (settings.py + config.py)
# ================================

from settings import USERID, TERMCODE, DISCORD_WEBHOOK, COOKIES

try:
    from config import (
        ROOT_URL,
        DESIRED,
        TRACKED,
        SWAP_MATRIX,
        CHECK_INTERVAL,
        KEEPALIVE_INTERVAL,
    )
except ImportError as exc:
    raise SystemExit(
        "config.py not found. Copy config.example.py to config.py and edit your courses."
    ) from exc

API = ROOT_URL + "subjects/{}/courses/{}/regblocks"
TARGET_DOMAIN = "tamu.collegescheduler.com"
LOGIN_URL = "https://tamu.collegescheduler.com/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://tamu.collegescheduler.com/",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

CURRENT_CLASSES = {}

class tracker:
    FAIL_COUNTER = 0 # If the script fails too many times, stop running

# ================================
# SESSION MANAGEMENT
# ================================

def initialize_session_from_browser():
    ''' Initialize session by copying cookies from browser. Called by main()'''
    
    # Compile all the cookies into the session
    for cookie_name, value in COOKIES.items():
        SESSION.cookies.set(cookie_name, value, domain=TARGET_DOMAIN)

    print(f"[{datetime.now()}] Session initialized with browser cookies")
    return True

def keep_session_alive():
    '''Make a lightweight request to keep the session active. This prevents the 30-minute timeout.'''
    try:
        # Visit the main page or make a simple API call
        r = SESSION.get("https://tamu.collegescheduler.com/", timeout=10)
        
        # Notify if keepalive successful
        if r.status_code == 200:
            print(f"[{datetime.now()}] Session keepalive successful")
            return True
        else:
            print(f"[{datetime.now()}] Session keepalive returned status {r.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Session keepalive failed: {e}")
        send_discord_message(f"⚠️ Session keepalive failed: {e}")
        tracker.FAIL_COUNTER += 1
        return False

# ================================
# OBTAIN A WEBSOCKET TOKEN
# ================================

def getToken():
    '''Obtain an authentication token. This is used to validate websocket connection. This function is called by start_websocket()'''
    try:
        # Make a request to the token api
        r = SESSION.get('https://tamu.collegescheduler.com/api/oauth/student/client-credentials/token', timeout=10)
        if r.status_code == 403:
            print("[ERROR] Session expired (403). Please restart with fresh cookies.")
            send_discord_message(f"@everyone Failed to get token when attempting to register.")
            return None
        r.raise_for_status()
        # If everything is good return the token
        return r.json()
    except Exception as e:
        print(f"[ERROR] Token request failed: {e}")
        tracker.FAIL_COUNTER += 1
        return None

def start_websocket(reg=None, course_name=None, course_num=None, method=None, current_class=None):
    '''Connect to the TAMU websocket. This is used to create a shopping cart and register classes.
    Valid methods: 
        cart (to send a course to shopping cart)
        action (to ensure no holds)
        register (to push the cart to registration)
        swap (to swap like-for-like courses)
        drop (to drop courses)'''
    
    # Get the cookies from the session
    cookie_header = "; ".join([f"{cookie.name}={cookie.value}" 
                                for cookie in SESSION.cookies])
    
    try:
        token = getToken()['accessToken']   # Get the token
    except:
        send_discord_message('[STATUS]: Critical error - could not retreive token')
        print('[STATUS]: Critical error - could not retreive token')
        token = ''

    def on_message(ws, message):
        # If the first message is a welcome message, do nothing
        if message.startswith('0{'):
            pass
        # When the host is ready, send the authorization token
        elif message == "40":
            ws.send(f'420["authorize",{{"token":"{token}"}}]')
        # Detect a failed attempt
        elif message.startswith('42["u') or message.startswith('430[{"success":false'):
            print('[ERROR] Websocket connection unauthorized')
            send_discord_message('⚠️ [ERROR] Websocket authentication failed')
        # If authorization is successful, send the data depending on what action was specified
        elif message.startswith('430[{"success":true') and 'success' in message:
            time.sleep(0.5)

            if method == 'cart':    # Push a course to the cart
                cart_request = {
                "cartName": "Aggie Schedule Builder Shopping Cart",
                "environment": "tamu",
                "nativeCartRequest": True,
                "sections": [{
                    "action": "PUT",
                    "sectionParameterValues": {
                        "units": 2,
                        "externalSectionId": "",
                        "externalCourseId": ""
                    },
                    "regNumber": reg,
                    "subjectCode": course_name,
                    "courseNumber": course_num,
                    "academicCareerCode": ""
                }],
                "termCode": TERMCODE,
                "userId": USERID
                }
                message = f'421["send-to-cart-request",{json.dumps(cart_request)}]'
            elif method == 'action':    # Check for holds/action items
                cart_request = {
                    "userId":USERID,
                    "termCode":TERMCODE,
                    "environment":"tamu"
                    }
                message = f'421["get-action-item-states-request",{json.dumps(cart_request)}]'
            elif method == 'register':  # Register the class
                cart_request = {
                    "subdomain":"tamu",
                    "type":"ENROLL_CART",
                    "userId":USERID,
                    "termCode":TERMCODE,
                    "additionalData":{"altPin":""}
                    }
                message = f'421["registration-request",{json.dumps(cart_request)}]'
            elif method == 'swap':  # Swap the section if already registered for course
                cart_request = {
                    "subdomain":"tamu",
                    "type":"ENROLL_CART",
                    "userId":USERID,
                    "termCode":TERMCODE,
                    "regNumberRequests":[{"regNumber":current_class,"action":"DW"},
                                         {"regNumber":reg}],
                    "additionalData":{"altPin":""},
                    "conditionalAddDrop":"Y"}
                message = f'421["registration-request",{json.dumps(cart_request)}]'
            elif method == 'drop':  # Drop the class
                cart_request = {
                    "regNumberRequests":
                    [
                        {"action":"DW",
                         "sectionParameterValues": {
                            "creditHour":"",
                            "gradingBasis":"",
                            "gradingMode":"",
                            "level":"",
                            "units":""},
                        "regNumber":current_class,
                        "academicCareerCode":""}
                    ],
                    "subdomain":"tamu",
                    "termCode":TERMCODE,
                    "type":"EDIT",
                    "userId":USERID,
                    "additionalData":{"altPin":""}
                }
                message = f'421["registration-request",{json.dumps(cart_request)}]'
            ws.send(message)
        
        # If we get a good response, then disconnect
        elif message.startswith('42'):
            fetch_classes()
            # Check to make sure the class was successfully added to the shopping cart and then registered
            if 'CURRENT_SCHEDULE_FAILURE' in str(message):  # Error in message automatically means failure
                print('[ERROR] Registration Failure')
                send_discord_message('An error occured during registration')
            elif 'send-to-cart-response' in str(message) and 'SUCCESS' in str(message):
                print(f'[CART] Successfully added {course_name} {course_num} to cart')
                send_discord_message(f'Successfully added {course_name} {course_num} to cart')
            # Get the current classes by sending a GET request (fetch_classes())
            elif CURRENT_CLASSES.get(f'{course_name} {course_num}') == reg:
                send_discord_message(f'@everyone 🎉 **REGISTRATION:** Successfully registered for {course_name} {course_num}!')
                print(f'[REGISTRATION] Successfully registered for {course_name} {course_num}!')
                send_discord_message(f'Removing {course_name} from tracked classes...')
                DESIRED.pop(f'{course_name} {course_num}')

            # Wait a bit then disconnect
            time.sleep(0.25)
            ws.send("41")
            ws.close()
            
        # If we get another kind of message, try and print it to see what it says
        else: 
            try:
                data = json.loads(message)
                print(f"   Response: {json.dumps(data, indent=2)}")
            except Exception as e:
                pass

    def error(ws, error):
        '''Catch websocket errors such as timeout'''
        if "timeout" in str(error).lower() or isinstance(error, TimeoutError):
            print(f"[ERROR] Websocket timeout during {method} operation")
            send_discord_message(f"⚠️ Websocket timeout during {method} for {course_name} {course_num}")
        else:
            print(f"[ERROR] Websocket error: {error}")
            send_discord_message(f"⚠️ Websocket error during {method}: {error}")
    
        ws.close()

    ws = websocket.WebSocketApp(
    "wss://api.collegescheduler.com/socket.io/?EIO=3&transport=websocket",
    header={
        "Host": "api.collegescheduler.com",
        "Upgrade": "websocket",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:145.0) Gecko/20100101 Firefox/145.0",
        "Sec-WebSocket-Version": '13',
        "Sec-WebSocket-Key": "e9frIxcpzu7+b4HCJ3algQ==",
        "Origin": "https://tamu.collegescheduler.com",
        "Cookie": cookie_header
    },
    on_message=on_message,
    on_error=error)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

# ================================
# SEND MESSAGE TO DISCORD
# ================================

def send_discord_message(message):
    """Send a message to a discord webhook."""
    data = {"content": message}
    try:
        requests.post(DISCORD_WEBHOOK, json=data)
    except Exception as e:
        print(f"[ERROR] Failed to send Discord message: {e}")

# ================================
# MAIN MONITOR LOOP
# ================================

def fetch_classes():
    '''This function fetches my current classes'''
    current_class_list = []
    try:
        classdata = fetch_json(ROOT_URL + 'currentschedule')
        for element in classdata:
            cNum = element['course']
            cName = element['subject']
            cSec = element['sectionNumber']
            crn = element['registrationNumber']
            instuctor = element['instructor'][0]['name']
            CURRENT_CLASSES[f'{cName} {cNum}'] = crn
            current_class_list.append(f'{cName} {cNum} (sec {cSec}) with {instuctor}')
        return ', '.join(current_class_list)
    except:
        print('[STATUS] Could not retrieve classes')
        send_discord_message('[STATUS] Could not retrieve classes')
        
def fetch_json(url):
    """Fetch JSON data from URL using the persistent session. This is the dictionary with the class availabilities"""
    try:
        r = SESSION.get(url, timeout=30)
        # Notify if we can't get the info
        if r.status_code == 403:
            print("[ERROR] Session expired (403). Please restart with fresh cookies.")
            send_discord_message(f"@everyone [ERROR] Session expired. Script needs restart with fresh cookies.")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        tracker.FAIL_COUNTER += 1
        return None

def summarize_sections(data):
    """Extract a summary for each section."""
    output = {}
    sections = data.get("sections", []) # Only look at the sections part of the json, other parts are unnecessary
    for sec in sections:    # Iterate through all individual sections
        sec_num = sec.get("sectionNumber", "UNKNOWN")   # Section number
        seats_cap = sec.get("seatsCapacity", None)      # Seating capacity
        seats_filled = sec.get("seatsFilled", None)     # Seats filled
        crn = sec.get('id')                             # Specific section ID
        instructor_name = None
        if "instructor" in sec and len(sec["instructor"]) > 0: # If a professor exists, get their name
            instructor_name = sec["instructor"][0].get("name")

        # Create a key for each section containing important information and store it in an output dictionary
        # This output dictionary contains all the sections and information for 1 course
        output[sec_num] = {
            "instructor": instructor_name,
            "capacity": seats_cap,
            "filled": seats_filled,
            "available": None if seats_cap is None or seats_filled is None else int(seats_cap) - int(seats_filled),
            'crn': crn
        }
    return output   # Return this outpt

def dict_diff(old, new, course):
    """Find differences between two snapshots. It will also determine if changes were made to a tracked section"""
    changes = []    # This list will contain all the changes to ALL sections
    mytracked = []  # This list will contain only the messages about the TRACKED sections
    mysections = [] # This list will only contain the course and section, instead of the text to send to the discord.

    # Check if a section was removed
    for sec in old:
        if sec not in new:
            changes.append(f"{course} Section {sec} was removed.")
            print(f'[{datetime.now()}] Update: {course} {sec} (Prof. {old[sec]["instructor"]}) was removed')
            # The following only applies to tracked courses
            if course in DESIRED and sec in DESIRED.get(course, ''):
                mytracked.append(f'‼️ **Changes to your desired section:** ‼️ @everyone {course} Section {sec}')
            elif course in TRACKED and sec in TRACKED.get(course, ''):
                mytracked.append(f'🔶**Changes to your tracked section:**🔶 @everyone {course} Section {sec}')

    # Check if a section was added
    for sec in new:
        if sec not in old:
            changes.append(f"New {course} section {sec} added with instructor {new[sec]['instructor']} and {new[sec]['available']} seats available.")
            print(f"[{datetime.now()}] Update: {course} {sec} added with instructor {new[sec]['instructor']} and {new[sec]['available']} spots.")
            # The following only applies to tracked courses
            if course in DESIRED and sec in DESIRED.get(course, ''):
                mytracked.append(f'‼️ **Changes to your desired section:** ‼️ @everyone {course} Section {sec}')
            elif course in TRACKED and sec in TRACKED.get(course, ''):
                mytracked.append(f'🔶**Changes to your tracked section:**🔶 @everyone {course} Section {sec}')

    # All other cases
    for sec in new:
        if sec in old:
            old_s = old[sec]
            new_s = new[sec]
            # If the instructor changed
            if old_s["instructor"] != new_s["instructor"]:
                changes.append(f"{course} Section {sec} instructor changed: {old_s['instructor']} → {new_s['instructor']}")
                print(f"[{datetime.now()}] Update: {course} {sec} (Prof. {new[sec]['instructor']}), Previous {old[sec]['instructor']}")
                # Only applies to tracked courses
                if course in DESIRED and sec in DESIRED[course]:
                    mytracked.append(f'‼️ **Changes to your desired section:** ‼️ @everyone {course} Section {sec}')
                elif course in TRACKED and sec in TRACKED[course]:
                    mytracked.append(f'🔶**Changes to your tracked section:**🔶 @everyone {course} Section {sec}')

            # If the capacity changed
            #if old_s["capacity"] != new_s["capacity"]:
            #    changes.append(f"{course} Section {sec} capacity changed: {old_s['capacity']} → {new_s['capacity']}")
            #    if course in DESIRED and sec in DESIRED[course]:
            #        mytracked.append(f'‼️ **Changes to your tracked section:** ‼️ @everyone {course} Section {sec}')
            # If the number of seats filled changes
            #if old_s["filled"] != new_s["filled"]:
            #    changes.append(f"{course} Section {sec} seats filled changed: {old_s['filled']} → {new_s['filled']}")
            #    if course in DESIRED and sec in DESIRED[course]:
            #        mytracked.append(f'‼️ **Changes to your tracked section:** ‼️ @everyone {course} Section {sec}')

            # If the number of seats available changes (usually most important change)

            if old_s["available"] != new_s["available"]:
                # Detect if a section opens
                if new_s['available'] > 0 and old_s['available'] <= 0:
                    # =====
                    # =====
                    # COMMENTING OUT NOTIFICATIONS, ITS ANNOYING
                    # =====
                    # =====
                    # changes.append(f"🟢 OPENED: {course} Section {sec}: {new_s['available']} seats available. {new_s['instructor']}")
                    # If this is the section I'm looking for, begin the process of registring
                    if course in DESIRED and sec in DESIRED[course]: 
                        mytracked.append(f'‼️ **Changes to your desired section:** ‼️ @everyone {course} Section {sec} {new_s["instructor"]}')
                        changes.append(f"{course} Section {sec}: {new_s['available']} seats available (was {old_s['available']}). {new_s['instructor']}")
                        mysections.append(course)         # Course Name
                        mysections.append(sec)             # Section
                        mysections.append(new_s['crn'])    # Registration number
                    elif course in TRACKED and sec in TRACKED[course]:
                        mytracked.append(f'🔶**Changes to your tracked section:**🔶 @everyone {course} Section {sec}')
                # Detect if a section closes
                elif new_s['available'] <= 0 and old_s['available'] > 0:
                    # changes.append(f"🔴 CLOSED: {course} Section {sec} {new_s['instructor']}")
                    pass
                # For any change, log it in the console for future reference
                print(f"[{datetime.now()}] Update: {course} {sec} (Prof. {new_s['instructor']}), {new_s['available']} spots. Previous {old_s['available']}")
    # Returns all changes to the course, the changes that I am interested, and the sections that I want to register for
    return changes, mytracked, mysections

def main():
    print("=== TAMU Course Monitor Started ===")
    print(f"Checking every 30-90 seconds.\n")
    send_discord_message('[STATUS]: Course Monitor Started')
    send_discord_message('[STATUS]: Logging in...')

    # Initialize session with browser cookies
    initialize_session_from_browser()
    print('Your classes: ', fetch_classes())
    send_discord_message(f'Your classes: {fetch_classes()}')

    # Format the snapshot dictionaries
    last_snapshot = {course: None for course in TRACKED}
    current_snapshot = {}
    last_keepalive = time.time()

    while True:
        # Keep session alive periodically
        if time.time() - last_keepalive > KEEPALIVE_INTERVAL:
            keep_session_alive()
            last_keepalive = time.time()

        print(f"[{datetime.now()}] Checking for updates...")

        # Iterate through all the courses in the class list
        for course in TRACKED:
            cName = course.split()[0]
            cNum = course.split()[1]
            data = fetch_json(API.format(cName, cNum))   # Fetch the json for a course from the website
            if not data:
                continue
            
            # Simplify the data. For example, it will be a dictionary of {'PHYS 206':{'508':{'instructor':'text','crn':'text', etc...}}}
            current_snapshot[course] = summarize_sections(data)

            # If the last snapshot exists, compare changes
            if last_snapshot[course] is not None:
                # Detect the differences between shapshots. Capture the information it sends back
                changes, mytracked, mysec = dict_diff(last_snapshot[course], current_snapshot[course], course)
                
                # Send a discord message with every change detected
                if changes:
                    for c in changes:
                        send_discord_message(f"🔔 **Update Detected:** {c}")

                # Send a special @mention discord message for changes that I am interested in
                if mytracked:
                    for entry in mytracked:
                        send_discord_message(entry)

                # If there is a class I want to register for, get the class information and send it via websocket to the website
                if mysec != []:
                    coursename = mysec[0].split()[0]    # The course name I want (PHYS)
                    coursenumber = mysec[0].split()[1]  # The course number I want (206)
                    crn = mysec[2]                      # The crn of the class I want
                    send_discord_message(f'Attempting to register you for {mysec[0]} section {mysec[1]}...')

                    # If we already have this course OR their is a conflicting time slot, we need to drop both first
                    if f'{coursename} {coursenumber}' in CURRENT_CLASSES:
                        # crn, coursename, and coursenumber are ignored for drop method
                        start_websocket(method='drop', current_class=CURRENT_CLASSES[f'{coursename} {coursenumber}'])
                        send_discord_message(f'Swapped course...')
                    if f'{coursename} {coursenumber}' in SWAP_MATRIX:
                        start_websocket(method='drop', current_class=SWAP_MATRIX[f'{coursename} {coursenumber}'])
                        send_discord_message(f'Dropped conflicting course...')

                    # Now we can register (time delay to avoid concurrent websocket connections)
                    time.sleep(1)
                    start_websocket(reg=crn, course_name=coursename, course_num=coursenumber, method='cart')
                    start_websocket(reg=crn, course_name=coursename, course_num=coursenumber, method='action')
                    start_websocket(reg=crn, course_name=coursename, course_num=coursenumber, method='register')

                    send_discord_message(f'Your current classes are now: {fetch_classes()}')
            # Store as the previous snapshot
            last_snapshot[course] = current_snapshot[course]

        if tracker.FAIL_COUNTER > 10:
            send_discord_message('[STATUS]: Critical error - check cookies. Stopping...')
            print('[STATUS]: Critical error - check cookies. Stopping...')
            break

        # Randomize check intervak
        CHECK_INTERVAL = 30 + 60*random.random()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()